import hashlib
from typing import List
from domain.search import SearchRequest, SearchContext
from domain.enums import SearchMode
from domain.route import Route
from domain.station import Station
from domain.station_identity import prefecture_full, station_name_prefecture
from domain.journey import canonical_station, station_names_match, unqualified_station_name
from application.ports.scraper_port import ScraperPort
from application.ports.cache_port import CachePort
from domain.exceptions import DomainException

from core.logger import logger
from application.services.route_families import group_route_families, categorize_routes
from application.services.direct_alternatives import DirectAlternativeDiscovery
from application.services.next_day_discovery import DISCOVERY_POLICY_VERSION, NextDayRouteDiscovery, contextualize_routes

class SearchModeResolver:
    @staticmethod
    def resolve(request: SearchRequest) -> SearchContext:
        if request.departure_date and request.departure_time:
            mode = SearchMode.ROUTE_WITH_DATETIME
        elif request.departure_time and not request.departure_date:
            mode = SearchMode.ROUTE_WITH_TIME
        else:
            mode = SearchMode.ROUTE_ONLY
            
        return SearchContext(
            departure_station=request.departure_station,
            arrival_station=request.arrival_station,
            departure_time=request.departure_time,
            departure_date=request.departure_date,
            search_mode=mode
        )

class SearchService:
    def __init__(self, scraper_port: ScraperPort, cache_port: CachePort, station_repo, cache_ttl: int = 3600):
        self.scraper_port = scraper_port
        self.cache_port = cache_port
        self.station_repo = station_repo
        self.cache_ttl = cache_ttl
        
    def _generate_cache_key(self, request: SearchRequest) -> str:
        origin = ('station-id', request.departure_station_id) if request.departure_station_id else ('legacy-name', canonical_station(request.departure_station))
        target = ('station-id', request.arrival_station_id) if request.arrival_station_id else ('legacy-name', canonical_station(request.arrival_station))
        # v5 cached HH:mm-only samples with the query date, including next-day
        # Yahoo departures. They cannot safely authorize the new date contract.
        # The policy marker also excludes the earlier unconditional v6 results;
        # the dated Route/timetable serialization itself remains unchanged.
        raw_key = repr(('families-v6', DISCOVERY_POLICY_VERSION, origin, target, request.departure_time, request.departure_date))
        return hashlib.md5(raw_key.encode()).hexdigest()

    async def _resolve_station(self, station_id: str | None, display_name: str) -> Station | None:
        if station_id:
            station = await self.station_repo.get_station_by_id(station_id)
            if not isinstance(station, Station):
                raise DomainException('Selected station identity is missing; select the station again')
            return station
        candidates = await self.station_repo.search_stations(display_name)
        exact = [s for s in candidates if s.name.casefold() == display_name.casefold()
                 or canonical_station(s.name_jp) == canonical_station(display_name)]
        if not exact:
            exact = [s for s in candidates if unqualified_station_name(s.name_jp) == canonical_station(display_name)]
        identities = {s.identity_key(): s for s in exact}
        if len(identities) > 1:
            raise DomainException('Ambiguous station identity; select a specific station ID')
        return next(iter(identities.values()), None)

    @staticmethod
    def _bind_station(selected: Station, returned: Station) -> Station:
        expected, actual = canonical_station(selected.name_jp), canonical_station(returned.name_jp or returned.name)
        region = prefecture_full(selected.prefecture) or station_name_prefecture(expected)
        returned_regions = {value for value in (prefecture_full(returned.prefecture), station_name_prefecture(actual)) if value}
        if ((region and any(value != region for value in returned_regions))
                or not station_names_match(expected, actual)
                or (unqualified_station_name(expected) != expected and unqualified_station_name(actual) == actual)):
            raise DomainException(f'Provider station identity mismatch: expected {expected}, returned {actual}')
        return selected.model_copy(update={'provider_ids': {**selected.provider_ids, **returned.provider_ids},
            'provider_aliases': {**selected.provider_aliases, **returned.provider_aliases}, 'platform': returned.platform})

    def _bind_endpoints(self, routes: list[Route], origin: Station | None, target: Station | None) -> list[Route]:
        verified = []
        for route in routes:
            if not route.stations:
                if origin or target:
                    logger.warning('Provider route lacks verifiable station identity')
                    continue
                verified.append(route)
                continue
            stations = list(route.stations)
            try:
                if origin:
                    stations[0] = self._bind_station(origin, stations[0])
                if target:
                    stations[-1] = self._bind_station(target, stations[-1])
            except DomainException as exc:
                logger.warning('%s', exc)
                continue
            verified.append(route.model_copy(update={'stations': stations,
                'departure_station': origin.name if origin else route.departure_station,
                'arrival_station': target.name if target else route.arrival_station}))
        if routes and not verified:
            raise DomainException('Provider station identity did not match the selected stations')
        return verified

    async def _get_jp_name(self, name_en: str) -> str:
        stations = await self.station_repo.search_stations(name_en)
        for s in stations:
            if s.name.lower() == name_en.lower():
                return s.name_jp
        return name_en

    async def _populate_independent_fares(self, routes: List[Route], departure_time: str, departure_date: str):
        import asyncio
        from core.logger import logger
        
        async def fetch_fare(route_idx, seg_idx, seg, dep_station: str, arr_station: str):
            try:
                dep_jp = await self._get_jp_name(dep_station)
                arr_jp = await self._get_jp_name(arr_station)
                
                indep_routes = await self.scraper_port.search_routes(
                    departure=dep_jp,
                    arrival=arr_jp,
                    time=departure_time,
                    date=departure_date
                )
                if indep_routes:
                    for r in indep_routes:
                        for s in r.segments:
                            if seg.railway_name and (seg.railway_name in s.railway_name or s.railway_name in seg.railway_name):
                                return route_idx, seg_idx, seg.model_copy(update={"base_fare": s.base_fare, "express_fare": s.express_fare})
                    if indep_routes[0].segments:
                        first_seg = indep_routes[0].segments[0]
                        return route_idx, seg_idx, seg.model_copy(update={"base_fare": first_seg.base_fare, "express_fare": first_seg.express_fare})
            except Exception as e:
                logger.error(f"Failed to fetch independent fare for {dep_station} -> {arr_station}: {e}")
            return route_idx, seg_idx, seg

        tasks = []
        for route_idx, r in enumerate(routes):
            if len(r.segments) > 1:
                for seg_idx, seg in enumerate(r.segments):
                    dep_station = r.stations[seg_idx].name
                    arr_station = r.stations[seg_idx+1].name
                    tasks.append(fetch_fare(route_idx, seg_idx, seg, dep_station, arr_station))
                    
        if tasks:
            logger.info(f"Fetching {len(tasks)} independent fares concurrently...")
            results = await asyncio.gather(*tasks)
            
            updates = {}
            for r_idx, s_idx, new_seg in results:
                if r_idx not in updates:
                    updates[r_idx] = list(routes[r_idx].segments)
                updates[r_idx][s_idx] = new_seg
                
            for r_idx, new_segments in updates.items():
                routes[r_idx] = routes[r_idx].model_copy(update={"segments": new_segments})

    async def search(self, request: SearchRequest) -> List[Route]:
        logger.info(f"Route Search Started: {request.departure_station} -> {request.arrival_station}")
        
        if (request.departure_station == request.arrival_station
                and request.departure_station_id == request.arrival_station_id):
            raise DomainException("Departure and arrival stations cannot be the same.")
        if not request.departure_date or not request.departure_time:
            raise DomainException("Route search requires an explicit departure date and time.")

        origin = await self._resolve_station(request.departure_station_id, request.departure_station)
        target = await self._resolve_station(request.arrival_station_id, request.arrival_station)
        request = request.model_copy(update={
            'departure_station': origin.name_jp if origin else request.departure_station,
            'arrival_station': target.name_jp if target else request.arrival_station,
            'departure_station_id': origin.id if origin else None,
            'arrival_station_id': target.id if target else None})
        if origin and target and origin.id == target.id:
            raise DomainException('Departure and arrival stations cannot be the same.')

        cache_key = self._generate_cache_key(request)
        cached_routes = await self.cache_port.get(cache_key)
        
        if cached_routes is not None:
            logger.info(f"Cache Hit for {request.departure_station} -> {request.arrival_station}")
            # Refresh presentation metadata without changing cache identity or
            # trusting cached provider endpoints over the current selected IDs.
            routes = self._bind_endpoints(cached_routes, origin, target)
            # This policy-versioned entry is the completed result collection.
            # Reinterpreting its recovered families as raw primary candidates
            # would restart optional exploration and lose the original frontier.
            for route in routes:
                await self.cache_port.set(route.id, route, ttl_seconds=self.cache_ttl)
            return routes
            
        logger.info(f"Cache Miss for {request.departure_station} -> {request.arrival_station}")
        
        dep_jp, arr_jp = request.departure_station, request.arrival_station
        
        logger.info(f"Scraper Started: {dep_jp} ({request.departure_station}) -> {arr_jp} ({request.arrival_station})")
        
        routes = await self.scraper_port.search_routes(
            departure=dep_jp,
            arrival=arr_jp,
            time=request.departure_time,
            date=request.departure_date
        )
        
        logger.info(f"Scraper Finished: Found {len(routes)} routes")
        
        routes = self._bind_endpoints(routes, origin, target)

        # Provider calendar evidence may place the actual departure tomorrow;
        # never overwrite that date with the original query calendar.
        routes = contextualize_routes(routes, request)
            
        # Route fares describe the discovery sample only. Re-searching every raw
        # segment amplified requests and still could not price a later selected train.
        # Keep existing primary-only direct evidence; enrichment never performs
        # per-family/per-leg timetable lookups. Use each route's effective date.
        alternatives = []
        if routes:
            alternatives = await DirectAlternativeDiscovery(self.scraper_port, self.cache_port).discover(group_route_families(routes), request)
        return await self._enrich_and_cache(routes + alternatives, request, origin, target, cache_key)

    async def _enrich_and_cache(self, routes: list[Route], request: SearchRequest,
                               origin: Station | None, target: Station | None, cache_key: str) -> list[Route]:
        supplemental = await NextDayRouteDiscovery(self.scraper_port, self.cache_port, self.cache_ttl).discover(request, routes)
        try:
            supplemental = self._bind_endpoints(supplemental, origin, target)
        except DomainException:
            logger.warning('Optional next-day discovery rejected: station identity mismatch')
            supplemental = []
        merged = routes + supplemental
        routes = categorize_routes(group_route_families(merged))
        logger.info('Route coverage: primary/cached=%d supplemental=%d merged=%d families=%d',
                    len(merged) - len(supplemental), len(supplemental), len(merged), len(routes))
        await self.cache_port.set(cache_key, routes, ttl_seconds=self.cache_ttl)
        for r in routes:
            await self.cache_port.set(r.id, r, ttl_seconds=self.cache_ttl)
            
        return routes

    async def get_route(self, route_id: str) -> Route:
        route = await self.cache_port.get(route_id)
        if not isinstance(route, Route):
            raise DomainException("Route expired or missing; search again")
        return route

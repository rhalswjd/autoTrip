import { useMutation } from '@tanstack/react-query';
import { createMovement } from '../api';
import type { MovementRequest } from '../api';

export function useMovement() {
  return useMutation({
    mutationFn: (data: MovementRequest) => createMovement(data),
  });
}

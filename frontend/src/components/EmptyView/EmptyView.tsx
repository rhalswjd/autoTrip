import './EmptyView.css';

interface EmptyViewProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
}

export function EmptyView({ icon, title, description }: EmptyViewProps) {
  return (
    <div className="empty-view">
      {icon && <div className="empty-view-icon">{icon}</div>}
      <h3 className="empty-view-title">{title}</h3>
      {description && <p className="empty-view-description">{description}</p>}
    </div>
  );
}

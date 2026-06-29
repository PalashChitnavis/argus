export default function StatusPill({ status }) {
  const isOnline = status === 'online';
  return (
    <span className={`status-pill ${isOnline ? 'online' : 'offline'}`}>
      <span className="status-dot" />
      {isOnline ? 'Online' : 'Offline'}
    </span>
  );
}

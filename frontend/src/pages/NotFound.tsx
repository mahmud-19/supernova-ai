import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div className="not-found">
      <div className="not-found-card">
        <div className="not-found-code">404</div>
        <h1 className="not-found-title">Page not found</h1>
        <p className="not-found-sub">The page you're looking for doesn't exist or you don't have access.</p>
        <Link to="/login" className="btn btn-primary">Go to Login</Link>
      </div>
    </div>
  );
}

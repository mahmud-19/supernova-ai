import { Navigate, Route, Routes } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Export } from './pages/Export';
import { NotFound } from './pages/NotFound';
import { Outcome } from './pages/Outcome';
import { Reannotate } from './pages/Reannotate';
import { Review } from './pages/Review';
import { ReviewList } from './pages/ReviewList';
import { Segmentation } from './pages/Segmentation';
import { Upload } from './pages/Upload';
import { Analytics } from './pages/Analytics';

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute roles={['sonologist', 'expert_reviewer']} />}>
          <Route path="/analytics" element={<Analytics />} />
        </Route>
        <Route element={<ProtectedRoute roles={['sonologist']} />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/cases/:id/segmentation" element={<Segmentation />} />
        </Route>
        <Route element={<ProtectedRoute roles={['expert_reviewer']} />}>
          <Route path="/review" element={<ReviewList />} />
          <Route path="/cases/:id/review" element={<Review />} />
          <Route path="/cases/:id/reannotate" element={<Reannotate />} />
          <Route path="/cases/:id/outcome" element={<Outcome />} />
          <Route path="/cases/:id/export" element={<Export />} />
        </Route>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  );
}

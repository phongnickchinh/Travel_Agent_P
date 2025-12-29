import { useLocation, useNavigate } from 'react-router-dom';
import AuthModal from '../components/auth/AuthModal';

export default function Welcome() {
  const location = useLocation();
  const navigate = useNavigate();

  const currentPath = location.pathname.toLowerCase();
  const mode =
    currentPath === '/register'
      ? 'register'
      : currentPath === '/reset-password'
        ? 'reset'
        : currentPath === '/login'
          ? 'login'
          : null;

  const handleClose = () => navigate('/', { replace: true });

  return (
    <div className="min-h-screen bg-white">
      <AuthModal open={Boolean(mode)} mode={mode || 'login'} onClose={handleClose} />
    </div>
  );
}

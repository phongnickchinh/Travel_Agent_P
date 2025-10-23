import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();

    if (loading) return <div>Đang kiểm tra đăng nhập...</div>;

    if (!user) return <Navigate to="/login" replace />;

    return children;
}

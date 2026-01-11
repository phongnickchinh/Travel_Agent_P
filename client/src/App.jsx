import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';

import TailwindTest from './pages/TailwindTest';
import ChangePassword from './pages/user/ChangePassword';
import CreatePlan from './pages/user/CreatePlan';
import Dashboard from './pages/user/Dashboard';
import PlanDetail from './pages/user/PlanDetail';
import ProfileSettings from './pages/user/ProfileSettings';
import Trash from './pages/user/Trash';
import Welcome from './pages/Welcome';


import './App.css';


import ThemeToggle from './components/ui/ThemeToggle';
import ProtectedRoute from './contexts/ProtectedRoute';

function App() {
  return (
    <Router>
      <Routes>
        {/* Guest/public routes rendered via welcome page + modal popups */}
        <Route path="/" element={<Welcome />} />
        <Route path="/login" element={<Welcome />} />
        <Route path="/register" element={<Welcome />} />
        <Route path="/reset-password" element={<Welcome />} />
        <Route path="/tailwind-test" element={<TailwindTest />} />
        <Route path="/shared/:shareToken" element={<PlanDetail />} />

        {/* Dashboard routes */}
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard/create-plan" element={<ProtectedRoute><CreatePlan /></ProtectedRoute>} />
        <Route path="/dashboard/plan/:planId" element={<ProtectedRoute><PlanDetail /></ProtectedRoute>} />
        <Route path="/dashboard/trash" element={<ProtectedRoute><Trash /></ProtectedRoute>} />

        <Route path="/dashboard/settings/profile" element={<ProtectedRoute><ProfileSettings /></ProtectedRoute>} />
        <Route path="/dashboard/settings/password" element={<ProtectedRoute><ChangePassword /></ProtectedRoute>} />
        {/* Legacy routes */}
        <Route path="/dashboard/:username" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />

        {/* Thêm các route yêu cầu auth khác ở đây */}
      </Routes>
      <ThemeToggle />
    </Router>
  );
}
export default App;

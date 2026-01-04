import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';

import TailwindTest from './pages/TailwindTest';
import CreatePlan from './pages/user/CreatePlan';
import CreatePlanNew from './pages/user/CreatePlanNew';
import Dashboard from './pages/user/Dashboard';
import PlanDetail from './pages/user/PlanDetail';
import Trash from './pages/user/Trash';
import Welcome from './pages/Welcome';
import ProfileSettings from './pages/user/ProfileSettings';
import ChangePassword from './pages/user/ChangePassword';

// Search Autocomplete Demo Pages (Week 3 Deliverable)
import SearchDemo from './components/SearchDemo';
import SearchExamples from './pages/SearchExamples';

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
        <Route path="/search-demo" element={<ProtectedRoute><SearchDemo /></ProtectedRoute>} />
        <Route path="/search-examples" element={<ProtectedRoute><SearchExamples /></ProtectedRoute>} />

        {/* Thêm các route yêu cầu auth khác ở đây */}
      </Routes>
      <ThemeToggle />
    </Router>
  );
}
export default App;

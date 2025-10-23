// src/layouts/DashboardLayout.jsx
import { Outlet } from 'react-router-dom';
import './DashboardLayout.css';

export default function DashboardLayout() {
    return (
    <>
        <div className="dashboard-container">
        <div className="dashboard-content">
            <Outlet />
        </div>
        </div>
    </>
    );
}

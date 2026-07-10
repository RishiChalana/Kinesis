import { NavLink, Route, Routes } from 'react-router-dom'
import WorkoutView from './WorkoutView'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import SessionDetail from './pages/SessionDetail'
import AuthBar from './components/AuthBar'
import './pages/dashboard.css'

export default function App() {
  return (
    <div className="app">
      <nav className="topnav">
        <span className="brand">KINESIS</span>
        <NavLink to="/" end>Workout</NavLink>
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/history">History</NavLink>
        <div className="spacer" />
        <AuthBar />
      </nav>
      <Routes>
        <Route path="/" element={<WorkoutView />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/history" element={<History />} />
        <Route path="/session/:id" element={<SessionDetail />} />
      </Routes>
    </div>
  )
}

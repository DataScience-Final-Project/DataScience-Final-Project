import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import WelcomePage from './components/WelcomePage.tsx'
import Login from './components/Login.tsx'
import Register from './components/Register.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import PropertyDetailsPage from './components/PropertyDetailsPage.tsx'

createRoot(document.getElementById('root')!).render(
    <ErrorBoundary>
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<WelcomePage />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/dashboard" element={<App />} />
                <Route path="/dashboard/properties/:propertyId" element={<PropertyDetailsPage />} />
        </Routes>
        </BrowserRouter>
    </ErrorBoundary>,
)

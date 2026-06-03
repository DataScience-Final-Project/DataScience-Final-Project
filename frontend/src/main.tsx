import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import WelcomePage from './components/WelcomePage.tsx'
import SignUp from './components/SignUp.tsx'
import Register from './components/Register.tsx'

createRoot(document.getElementById('root')!).render(
    <BrowserRouter>
        <Routes>
            <Route path="/" element={<WelcomePage />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/register" element={<Register />} />
            <Route path="/dashboard" element={<App />} />
        </Routes>
    </BrowserRouter>,
)

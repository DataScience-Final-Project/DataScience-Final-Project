import { useNavigate } from 'react-router-dom';
import { Button } from 'antd';
import propCastLogo from '../assets/propCastLogo.png';
import './WelcomePage.css';

const WelcomePage = () => {
  const navigate = useNavigate();

  return (
    <div className="welcome-shell">
      <div className="welcome-card">
        <div className="welcome-brand">
          <img src={propCastLogo} alt="PropCast" className="welcome-logo" />
          
          <p className="welcome-subtitle">Smarter real estate investment insights</p>
        </div>

        <div className="welcome-actions">
          <Button
            type="primary"
            size="large"
            block
            className="welcome-btn welcome-btn--primary"
            onClick={() => navigate('/login')}
          >
            Log In
          </Button>
          <Button
            size="large"
            block
            className="welcome-btn welcome-btn--ghost"
            onClick={() => navigate('/register')}
          >
            Register
          </Button>
        </div>
      </div>
    </div>
  );
};

export default WelcomePage;

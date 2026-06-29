import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, ConfigProvider, Form, Input, message } from 'antd';
import propCastLogo from '../assets/propCastLogo.png';
import { dashboardTheme } from '../dashboardTheme';
import { login, setCurrentUser, type LoginPayload } from '../api/auth';
import './Auth.css';

const Login = () => {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: LoginPayload) => {
    setSubmitting(true);
    try {
      const { user } = await login({
        identifier: values.identifier.trim(),
        password: values.password,
      });
      setCurrentUser(user);
      message.success(`Welcome back, ${user.firstName}!`);
      navigate('/dashboard');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ConfigProvider theme={dashboardTheme}>
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-header">
            <img
              src={propCastLogo}
              alt="PropCast"
              className="auth-logo"
              onClick={() => navigate('/')}
            />
            <h1 className="auth-title">Log In</h1>
            <p className="auth-subtitle">Welcome back to PropCast</p>
          </div>

          <Form
            className="auth-form"
            layout="vertical"
            requiredMark={false}
            onFinish={onFinish}
          >
            <Form.Item
              label="Email, username or phone"
              name="identifier"
              rules={[{ required: true, message: 'Please enter your email, username or phone' }]}
            >
              <Input size="large" placeholder="you@example.com" autoComplete="username" />
            </Form.Item>

            <Form.Item
              label="Password"
              name="password"
              rules={[{ required: true, message: 'Please enter your password' }]}
            >
              <Input.Password size="large" placeholder="••••••••" autoComplete="current-password" />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                size="large"
                block
                htmlType="submit"
                loading={submitting}
                className="auth-submit"
              >
                Log In
              </Button>
            </Form.Item>
          </Form>

          <div className="auth-footer">
            Don't have an account?{' '}
            <button type="button" className="auth-link" onClick={() => navigate('/register')}>
              Register
            </button>
          </div>
        </div>
      </div>
    </ConfigProvider>
  );
};

export default Login;

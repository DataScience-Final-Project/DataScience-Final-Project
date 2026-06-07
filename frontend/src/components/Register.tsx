import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, ConfigProvider, Form, Input, message } from 'antd';
import propCastLogo from '../assets/propCastLogo.png';
import { dashboardTheme } from '../dashboardTheme';
import { signup, type SignupPayload } from '../api/auth';
import './Auth.css';

const Register = () => {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: SignupPayload) => {
    setSubmitting(true);
    try {
      const { user } = await signup({
        email: values.email.trim(),
        phone: values.phone.trim(),
        username: values.username.trim(),
        firstName: values.firstName.trim(),
        lastName: values.lastName.trim(),
        password: values.password,
      });
      message.success(`Welcome, ${user.firstName}!`);
      navigate('/dashboard');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Registration failed');
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
            <h1 className="auth-title">Register</h1>
            <p className="auth-subtitle">Create your PropCast account</p>
          </div>

          <Form
            className="auth-form"
            layout="vertical"
            requiredMark={false}
            onFinish={onFinish}
          >
            <Form.Item
              label="First name"
              name="firstName"
              rules={[
                { required: true, message: 'Please enter your first name' },
                { max: 50, message: 'First name must be 50 characters or less' },
              ]}
            >
              <Input size="large" placeholder="Jane" autoComplete="given-name" />
            </Form.Item>

            <Form.Item
              label="Last name"
              name="lastName"
              rules={[
                { required: true, message: 'Please enter your last name' },
                { max: 50, message: 'Last name must be 50 characters or less' },
              ]}
            >
              <Input size="large" placeholder="Doe" autoComplete="family-name" />
            </Form.Item>

            <Form.Item
              label="Email"
              name="email"
              rules={[
                { required: true, message: 'Please enter your email' },
                { type: 'email', message: 'Please enter a valid email' },
              ]}
            >
              <Input size="large" placeholder="you@example.com" autoComplete="email" />
            </Form.Item>

            <Form.Item
              label="Phone"
              name="phone"
              rules={[
                { required: true, message: 'Please enter your phone' },
                { min: 6, max: 30, message: 'Phone must be between 6 and 30 characters' },
              ]}
            >
              <Input size="large" placeholder="+972 50 000 0000" autoComplete="tel" />
            </Form.Item>

            <Form.Item
              label="Username"
              name="username"
              rules={[
                { required: true, message: 'Please choose a username' },
                { min: 3, max: 50, message: 'Username must be between 3 and 50 characters' },
              ]}
            >
              <Input size="large" placeholder="janedoe" autoComplete="username" />
            </Form.Item>

            <Form.Item
              label="Password"
              name="password"
              rules={[
                { required: true, message: 'Please enter a password' },
                { min: 8, message: 'Password must be at least 8 characters' },
              ]}
            >
              <Input.Password size="large" placeholder="••••••••" autoComplete="new-password" />
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
                Create account
              </Button>
            </Form.Item>
          </Form>

          <div className="auth-footer">
            Already have an account?{' '}
            <button type="button" className="auth-link" onClick={() => navigate('/login')}>
              Log In
            </button>
          </div>
        </div>
      </div>
    </ConfigProvider>
  );
};

export default Register;

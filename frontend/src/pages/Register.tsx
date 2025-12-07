import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../lib/api';
import { Button, Input } from '../components/ui';

const Register: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError("Passwords don't match");
            return;
        }

        setLoading(true);

        try {
            await register({ email, password });
            navigate('/login');
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || 'Registration failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-100">
            <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
                <div className="mb-6 text-center">
                    <h1 className="text-3xl font-bold text-gray-800">ParagonOCR</h1>
                    <p className="text-gray-500">Create a new account</p>
                </div>

                {error && (
                    <div className="mb-4 rounded bg-red-100 p-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <Input
                            id="email"
                            type="email"
                            label="Email"
                            placeholder="Enter your email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div className="mb-4">
                        <Input
                            id="password"
                            type="password"
                            label="Password"
                            placeholder="Create a password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <div className="mb-6">
                        <Input
                            id="confirmPassword"
                            type="password"
                            label="Confirm Password"
                            placeholder="Confirm your password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            error={password !== confirmPassword && confirmPassword ? "Passwords don't match" : undefined}
                            required
                        />
                    </div>

                    <Button
                        type="submit"
                        disabled={loading}
                        isLoading={loading}
                        className="w-full"
                        size="lg"
                    >
                        {loading ? 'Creating Account...' : 'Register'}
                    </Button>
                </form>

                <div className="mt-4 text-center text-sm">
                    <p className="text-gray-600">
                        Already have an account?{' '}
                        <Link to="/login" className="font-bold text-blue-600 hover:text-blue-800">
                            Sign In
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Register;

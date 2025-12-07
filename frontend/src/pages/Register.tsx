import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register, fetchMe } from '../lib/api';
import { useAuthStore } from '../store/authStore';
import { Button, Input } from '../components/ui';
import PasskeyRegistration from '../components/PasskeyRegistration';

const Register: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [showPasskeyOption, setShowPasskeyOption] = useState(false);
    const [passkeyRegistered, setPasskeyRegistered] = useState(false);

    const navigate = useNavigate();
    const { login: loginAction } = useAuthStore();

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
            // After registration, show passkey option
            setShowPasskeyOption(true);
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
                        disabled={loading || showPasskeyOption}
                        isLoading={loading}
                        className="w-full"
                        size="lg"
                    >
                        {loading ? 'Creating Account...' : 'Register'}
                    </Button>
                </form>

                {showPasskeyOption && !passkeyRegistered && (
                    <>
                        <div className="my-6 flex items-center">
                            <div className="flex-1 border-t border-gray-300"></div>
                            <span className="px-4 text-sm text-gray-500">Optional</span>
                            <div className="flex-1 border-t border-gray-300"></div>
                        </div>
                        <div className="mb-4">
                            <p className="mb-3 text-sm text-gray-600">
                                Register a passkey for faster, more secure login:
                            </p>
                            <PasskeyRegistration
                                deviceName={`${email.split('@')[0]}'s device`}
                                onSuccess={() => {
                                    setPasskeyRegistered(true);
                                    setTimeout(() => {
                                        navigate('/login');
                                    }, 1500);
                                }}
                                onError={(err) => setError(err)}
                            />
                        </div>
                        <Button
                            type="button"
                            onClick={() => navigate('/login')}
                            variant="secondary"
                            className="w-full"
                            size="lg"
                        >
                            Skip and Continue to Login
                        </Button>
                    </>
                )}

                {passkeyRegistered && (
                    <div className="mb-4 rounded bg-green-100 p-3 text-sm text-green-700">
                        Passkey registered successfully! Redirecting to login...
                    </div>
                )}

                {!showPasskeyOption && (
                    <div className="mt-4 text-center text-sm">
                        <p className="text-gray-600">
                            Already have an account?{' '}
                            <Link to="/login" className="font-bold text-blue-600 hover:text-blue-800">
                                Sign In
                            </Link>
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Register;

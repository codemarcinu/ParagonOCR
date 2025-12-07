import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { fetchMe } from '../lib/api';
import PasskeyRegistration from '../components/PasskeyRegistration';

const Register: React.FC = () => {
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [passkeyRegistered, setPasskeyRegistered] = useState(false);

    const navigate = useNavigate();
    const { login: loginAction } = useAuthStore();

    const handlePasskeySuccess = async (tokenData: any) => {
        try {
            const token = tokenData.access_token || tokenData.token?.access_token;
            if (!token) {
                throw new Error('No token received');
            }
            
            // Set token and fetch user
            useAuthStore.getState().setToken(token);
            const user = await fetchMe();
            loginAction(token, user);
            
            setPasskeyRegistered(true);
            setTimeout(() => {
                navigate('/');
            }, 1500);
        } catch (err: any) {
            console.error('Error after passkey registration:', err);
            setError(err.message || 'Failed to complete registration');
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-100">
            <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
                <div className="mb-6 text-center">
                    <h1 className="text-3xl font-bold text-gray-800">ParagonOCR</h1>
                    <p className="text-gray-500">Create a new account with passkey</p>
                </div>

                {error && (
                    <div className="mb-4 rounded bg-red-100 p-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {passkeyRegistered ? (
                    <div className="mb-4 rounded bg-green-100 p-3 text-sm text-green-700">
                        Passkey registered successfully! Redirecting...
                    </div>
                ) : (
                    <div className="mb-4">
                        <p className="mb-4 text-sm text-gray-600">
                            Register using your device's biometric authentication (Face ID, Touch ID, Windows Hello, etc.)
                        </p>
                        <PasskeyRegistration
                            deviceName="My Device"
                            onSuccess={handlePasskeySuccess}
                            onError={(err) => setError(err)}
                        />
                    </div>
                )}

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

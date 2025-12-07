import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import PasskeyLogin from '../components/PasskeyLogin';

const Login: React.FC = () => {
    const [error, setError] = useState('');

    const navigate = useNavigate();

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-100">
            <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
                <div className="mb-6 text-center">
                    <h1 className="text-3xl font-bold text-gray-800">ParagonOCR</h1>
                    <p className="text-gray-500">Sign in with passkey</p>
                </div>

                {error && (
                    <div className="mb-4 rounded bg-red-100 p-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                <div className="mb-6">
                    <PasskeyLogin
                        onSuccess={() => navigate('/')}
                        onError={(err) => setError(err)}
                    />
                </div>

                <div className="mt-4 text-center text-sm">
                    <p className="text-gray-600">
                        Don't have an account?{' '}
                        <Link to="/register" className="font-bold text-blue-600 hover:text-blue-800">
                            Register
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;

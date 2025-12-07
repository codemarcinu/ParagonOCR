import React, { useState } from 'react';
import { startRegistration } from '@simplewebauthn/browser';
import { getPasskeyRegistrationOptions, verifyPasskeyRegistration } from '../lib/api';
import { Button } from './ui';

interface PasskeyRegistrationProps {
  deviceName?: string;
  onSuccess?: (tokenData?: any) => void;
  onError?: (error: string) => void;
  className?: string;
}

const PasskeyRegistration: React.FC<PasskeyRegistrationProps> = ({
  deviceName,
  onSuccess,
  onError,
  className,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    setLoading(true);
    setError(null);

    try {
      // Check if WebAuthn is supported
      if (!window.PublicKeyCredential) {
        throw new Error('WebAuthn is not supported in this browser');
      }

      // Get registration options from server
      const options = await getPasskeyRegistrationOptions(deviceName);

      // Start registration using SimpleWebAuthn
      const credential = await startRegistration(options);

      // Verify registration with server
      const result = await verifyPasskeyRegistration({
        credential,
        challenge: options.challenge,
      });

      if (result.success || result.access_token) {
        // Pass token data to onSuccess callback
        onSuccess?.(result);
      } else {
        throw new Error(result.message || 'Registration failed');
      }
    } catch (err: any) {
      let errorMessage = 'Failed to register passkey';
      
      if (err.name === 'NotSupportedError') {
        errorMessage = 'Passkeys are not supported on this device. Please use a different authentication method.';
      } else if (err.name === 'NotAllowedError' || err.message?.includes('timeout') || err.message?.includes('not allowed')) {
        errorMessage = 'Operation was canceled, timed out, or not allowed. Please try again and make sure to complete the biometric prompt.';
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      onError?.(errorMessage);
      
      console.error('Passkey registration error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={className}>
      {error && (
        <div className="mb-4 rounded bg-red-100 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <Button
        type="button"
        onClick={handleRegister}
        disabled={loading}
        isLoading={loading}
        className="w-full"
        size="lg"
      >
        {loading ? 'Registering Passkey...' : 'Register Passkey'}
      </Button>
      <p className="mt-2 text-xs text-gray-500">
        Use your device's biometric authentication (Face ID, Touch ID, Windows Hello, etc.)
      </p>
    </div>
  );
};

export default PasskeyRegistration;


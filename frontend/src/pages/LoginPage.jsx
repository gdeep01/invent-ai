import { useGoogleLogin } from '@react-oauth/google'
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { toast } from 'sonner'

import LoginForm from '@/components/ui/login-form'
import { useAuth } from '@/context/AuthContext'

export default function LoginPage() {
  const auth = useAuth()
  const [isSigningIn, setIsSigningIn] = useState(false)

  const googleLogin = useGoogleLogin({
    onSuccess: async (credentialResponse) => {
      try {
        setIsSigningIn(true)
        await auth.login(credentialResponse)
        toast.success('Signed in successfully')
      } catch (error) {
        toast.error(error.message)
      } finally {
        setIsSigningIn(false)
      }
    },
    onError: () => {
      setIsSigningIn(false)
      toast.error('Sign in failed. Please try again.')
    },
  })

  if (!auth.isLoading && auth.isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-screen bg-white">
      <LoginForm
        onGoogleLogin={() => {
          setIsSigningIn(true)
          googleLogin()
        }}
        isLoading={isSigningIn || auth.isLoading}
      />
    </div>
  )
}

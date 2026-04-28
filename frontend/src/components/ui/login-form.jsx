import { LoaderCircle } from 'lucide-react'

export default function LoginForm({ onGoogleLogin, isLoading }) {
  return (
    <div className="grid min-h-screen w-full md:grid-cols-2">
      <section className="relative flex h-48 bg-gray-950 px-6 py-10 text-white md:h-screen md:px-16">
        <div className="absolute left-10 top-10 text-2xl font-semibold tracking-tight text-white">
          InventAI
        </div>

        <div className="flex w-full items-center">
          <div className="max-w-md">
            <h1 className="mt-0 text-4xl font-semibold leading-tight text-white">
              The inventory brain for modern retail.
            </h1>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-gray-500">
              Forecast demand, track mandi prices, and chat with your data - all in one place.
            </p>

            <div className="mt-12">
              <div className="flex items-center text-sm text-gray-400">
                <span className="mr-3 inline-block h-1.5 w-1.5 rounded-full bg-teal-400" />
                <span>ARIMA demand forecasting</span>
              </div>
              <div className="mt-4 flex items-center text-sm text-gray-400">
                <span className="mr-3 inline-block h-1.5 w-1.5 rounded-full bg-teal-400" />
                <span>Live mandi price tracking</span>
              </div>
              <div className="mt-4 flex items-center text-sm text-gray-400">
                <span className="mr-3 inline-block h-1.5 w-1.5 rounded-full bg-teal-400" />
                <span>AI inventory assistant</span>
              </div>
            </div>
          </div>
        </div>

        <div className="absolute bottom-10 left-10 text-xs text-gray-700">
          &copy; 2025 InventAI
        </div>
      </section>

      <section className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-white px-12 py-12 md:min-h-screen">
        <div className="w-full max-w-md">
          <h2 className="text-3xl font-semibold text-gray-900">Welcome back</h2>
          <p className="mt-2 text-sm text-gray-400">Sign in to continue to InventAI</p>

          <button
            type="button"
            onClick={onGoogleLogin}
            disabled={isLoading}
            className="mt-10 flex h-12 w-full items-center justify-center gap-3 rounded-lg border border-gray-200 bg-white text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isLoading ? (
              <LoaderCircle className="h-4 w-4 animate-spin text-gray-500" />
            ) : (
              <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 24 24">
                <path fill="#EA4335" d="M12 10.2v3.9h5.4c-.2 1.3-1.5 3.9-5.4 3.9-3.2 0-5.9-2.7-5.9-6s2.7-6 5.9-6c1.8 0 3 .8 3.7 1.5l2.5-2.4C16.6 3.5 14.5 2.7 12 2.7A9.3 9.3 0 0 0 2.7 12 9.3 9.3 0 0 0 12 21.3c5.4 0 9-3.8 9-9 0-.6-.1-1.1-.2-1.6z" />
                <path fill="#34A853" d="M2.7 16.3 5.8 14a5.6 5.6 0 0 0 10.5 0l3.1 2.4A9.3 9.3 0 0 1 12 21.3 9.3 9.3 0 0 1 2.7 16.3z" />
                <path fill="#4A90E2" d="M19.3 7.5 16.2 9.8A5.6 5.6 0 0 0 12 6.4c-1.5 0-2.9.6-3.9 1.6L5 5.6A9.3 9.3 0 0 1 12 2.7c3 0 5.6 1.1 7.3 2.8z" />
                <path fill="#FBBC05" d="M2.7 7.7A9.3 9.3 0 0 0 2.7 16.3L5.8 14A5.6 5.6 0 0 1 5.5 12c0-.7.1-1.4.3-2L2.7 7.7z" />
              </svg>
            )}
            <span>Continue with Google</span>
          </button>

          <p className="mt-6 text-center text-xs text-gray-400">
            Secure sign-in powered by Google
          </p>
        </div>
      </section>
    </div>
  )
}

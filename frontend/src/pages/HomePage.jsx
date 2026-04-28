import { Link } from 'react-router-dom'
import { HeroSection } from '@/components/blocks/hero-section'
import { Button } from '@/components/ui/button'

const features = [
  {
    title: 'Demand Forecasting',
    description:
      'ARIMA models trained on your sales history predict stock needs up to 30 days out - automatically.',
  },
  {
    title: 'Mandi Price Intelligence',
    description:
      'Live commodity price feeds from OGD India. Know when to buy more before prices spike.',
  },
  {
    title: 'AI Inventory Chat',
    description:
      'Ask your inventory anything in plain English. Reorder suggestions, trend analysis, and alerts - instantly.',
  },
]

const steps = [
  {
    number: '01',
    title: 'Upload',
    description: 'Drop your CSV. Any format, any column names.',
  },
  {
    number: '02',
    title: 'Forecast',
    description: 'ARIMA runs automatically. Results in under 60 seconds.',
  },
  {
    number: '03',
    title: 'Monitor',
    description: 'Live mandi prices and anomaly alerts keep you ahead.',
  },
  {
    number: '04',
    title: 'Act',
    description: 'AI generates plain-English reorder recommendations.',
  },
]

export default function HomePage() {
  return (
    <div className="bg-gray-950 text-white">
      <HeroSection />

      <main>
        <section id="features" className="bg-gray-950 py-32">
          <div className="mx-auto max-w-6xl px-6 md:px-16">
            <div className="max-w-2xl">
              <p className="mb-3 font-akzidenz text-xs uppercase tracking-[0.2em] text-teal-400">What It Does</p>
              <h2 className="mt-3 font-sans text-4xl font-semibold leading-tight tracking-normal text-white md:text-5xl">
                Everything you need to stock smarter
              </h2>
            </div>
            <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-3">
              {features.map((feature) => (
                <article
                  key={feature.title}
                  className="border-l-2 border-teal-400/20 bg-transparent p-0 pl-6 transition-colors duration-300 hover:border-teal-400/60"
                >
                  <h3 className="font-sans text-lg font-semibold tracking-normal text-white">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-gray-500">{feature.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="bg-gray-900/50 py-32">
          <div className="mx-auto max-w-6xl px-6 md:px-16">
            <div className="max-w-2xl">
              <p className="mb-3 font-akzidenz text-xs uppercase tracking-[0.2em] text-teal-400">How It Works</p>
              <h2 className="font-sans text-4xl font-semibold leading-tight tracking-normal text-white md:text-5xl">
                From upload to insight in minutes
              </h2>
            </div>
            <div className="relative mt-24 grid grid-cols-1 gap-0 md:grid-cols-4">
              {steps.map((step) => (
                <div
                  key={step.number}
                  className="relative px-8 first:pl-0 last:pr-0"
                >
                  <div className="font-akzidenz text-6xl font-bold leading-none text-teal-400/20">{step.number}</div>
                  <h3 className="mt-4 font-sans text-base font-semibold tracking-normal text-white">{step.title}</h3>
                  <p className="mt-1 max-w-xs font-sans text-sm leading-relaxed text-gray-500">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-gray-950 py-32">
          <div className="mx-auto max-w-4xl px-6 text-center lg:px-12">
            <h2 className="text-4xl font-black tracking-tight text-white md:text-5xl">Stop guessing.</h2>
            <p className="text-4xl font-black tracking-tight text-teal-400 md:text-5xl">Start knowing.</p>
            <p className="mx-auto mt-6 max-w-2xl text-base text-gray-400 md:text-lg">
              InventAI helps Indian retailers forecast demand, track price shifts, and act faster with confidence.
            </p>
            <div className="mt-10">
              <Button asChild size="lg" className="rounded-full bg-teal-400 px-8 py-3 text-base font-semibold text-gray-950 hover:bg-teal-300">
                <Link to="/upload">Get Started</Link>
              </Button>
            </div>
            <p className="mt-5 text-sm text-gray-500">Powered by ARIMA &middot; Gemini AI &middot; OGD India</p>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/5 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 md:flex-row md:px-16">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold tracking-tight text-white">InventAI</span>
            <span className="text-white/10">|</span>
            <span className="text-sm text-gray-600">&copy; 2025</span>
          </div>
          <div className="text-center">
            <p className="text-xs uppercase tracking-widest text-gray-600">
              Powered by ARIMA &middot; Gemini AI &middot; OGD India
            </p>
          </div>
         
        </div>
      </footer>
    </div>
  )
}

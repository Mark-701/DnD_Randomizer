import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import App from './App.jsx'

import {
  AnalyticsProvider,
  ErrorBoundary,
  ErrorReporterProvider,
  FeatureFlagsProvider,
  ga4Adapter,
  plausibleAdapter,
  createHttpErrorReporter,
} from '@kaldyrr/react-modules'

import {
  BrowserConsoleProvider,
  BrowserConsoleWindow,
  ConsoleErrorBoundary,
} from '@kaldyrr/react-modules/browser-console'

const reportError = createHttpErrorReporter({
  endpoint: import.meta.env.VITE_ERROR_ENDPOINT,
  app: 'my-react-app',
  release: import.meta.env.VITE_APP_VERSION,
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorReporterProvider reportError={reportError}>
      <ErrorBoundary>
        <BrowserConsoleProvider
          persist
          captureOptions={{ captureFetch: true }}
        >
          <ConsoleErrorBoundary>
            <AnalyticsProvider
              adapters={[
                ga4Adapter({ measurementId: 'G-XXXXXXXXXX' }),
                plausibleAdapter(),
              ]}
            >
              <FeatureFlagsProvider endpoint="/config/feature-flags.json">
                <App />
              </FeatureFlagsProvider>
            </AnalyticsProvider>
          </ConsoleErrorBoundary>
          <BrowserConsoleWindow defaultOpen={false} hotkey="F9" />
        </BrowserConsoleProvider>
      </ErrorBoundary>
    </ErrorReporterProvider>
  </React.StrictMode>,
)
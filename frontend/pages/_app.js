import '../src/styles/globals.css'
import { ToastProvider } from '../src/components/ui/ToastProvider'

export default function App({ Component, pageProps }) {
  return (
    <ToastProvider>
      <Component {...pageProps} />
    </ToastProvider>
  )
}
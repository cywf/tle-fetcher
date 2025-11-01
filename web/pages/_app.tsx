import '@/styles/globals.css'
import type { AppProps } from 'next/app'
import Head from 'next/head'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>TLE Pass Dashboard - Satellite Tracker</title>
        <meta name="description" content="Real-time satellite pass prediction and tracking dashboard" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/tle-fetcher/favicon.ico" />
      </Head>
      <Component {...pageProps} />
    </>
  )
}

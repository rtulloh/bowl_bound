import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { DetachedCharts } from './components/ChartViewer'
import './styles/index.css'

const chartRequest = new URLSearchParams(window.location.search)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {chartRequest.has('charts')
      ? <DetachedCharts gameId={chartRequest.get('charts')} initialSide={chartRequest.get('side')} initialChart={chartRequest.get('view')} />
      : <App />}
  </React.StrictMode>,
)

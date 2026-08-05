import { Outlet, Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { pipelineApi } from '../../services/api'

export default function Layout() {
  const location = useLocation()
  const [datasetInfo, setDatasetInfo] = useState<{
    generated: string | null
    totalRecords: number
  }>({ generated: null, totalRecords: 0 })

  useEffect(() => {
    const fetchDatasetInfo = async () => {
      try {
        const status = await pipelineApi.getStatus()
        if (status.upload_timestamp) {
          // Format timestamp for display
          const date = new Date(status.upload_timestamp)
          const formatted = date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })
          setDatasetInfo({
            generated: formatted,
            totalRecords: status.results?.total_records || 0
          })
        } else {
          // Reset when no data
          setDatasetInfo({
            generated: null,
            totalRecords: 0
          })
        }
      } catch (err) {
        // Keep default values if API fails
        console.error('Failed to fetch dataset info:', err)
      }
    }
    fetchDatasetInfo()

    // Also set up periodic refresh (every 10 seconds)
    const interval = setInterval(fetchDatasetInfo, 10000)

    return () => clearInterval(interval)
  }, [location.pathname]) // Refresh on route change

  const navItems = [
    { path: '/', label: 'Risk Overview', icon: '📊' },
    { path: '/investigation', label: 'Investigation', icon: '🔍' },
    { path: '/pipeline', label: 'Data Pipeline', icon: '🔄' },
    { path: '/model', label: 'Model Monitoring', icon: '🧠' },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16">
            {/* Left: Logo and Title */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
                  <span className="text-white text-sm font-bold">ML</span>
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-slate-900">
                    Risk Intelligence Platform
                  </h1>
                  <p className="text-xs text-slate-500">
                    Multi-Signal Risk Detection with Explainable Investigation
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-slate-200 min-h-screen flex flex-col">
          <nav className="p-4 space-y-1 flex-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === item.path
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Dataset Information - Bottom Left */}
          <div className="p-4 border-t border-slate-200 bg-slate-50">
            <div className="space-y-2 text-xs">
              <p className="font-semibold text-slate-700">Dataset Information</p>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-500">Source:</span>
                  <span className="text-slate-700">Uploaded Dataset</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Processing:</span>
                  <span className="text-slate-700">Risk Analytics Pipeline</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Update:</span>
                  <span className="text-slate-700">Manual Upload</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Generated:</span>
                  <span className="text-slate-700">
                    {datasetInfo.generated || 'No data uploaded'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Records:</span>
                  <span className="text-slate-700">
                    {datasetInfo.totalRecords > 0 ? datasetInfo.totalRecords.toLocaleString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-8 bg-slate-50/50">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

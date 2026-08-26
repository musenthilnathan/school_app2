import { useEffect, useMemo, useState } from 'react'
import './App.css'
import Login from './Login'

// Empty string means same-origin (used when the backend serves the built frontend in prod)
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const STATUS_CLASS = {
  READY_FOR_PICKUP: 'status-ready',
  APPROVED: 'status-approved',
  BOOK_HANDED_OVER: 'status-handed-over',
  PENDING_SWAP: 'status-pending',
}

const STATUS_TEXT = {
  READY_FOR_PICKUP: 'Ready',
  APPROVED: 'Approved',
  BOOK_HANDED_OVER: 'Handed Over',
  PENDING_SWAP: 'Pending Swap',
}

function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [query, setQuery] = useState('')
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)

  // Check for existing auth on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    if (storedToken && storedUser) {
      setToken(storedToken)
      setUser(JSON.parse(storedUser))
    }
  }, [])

  const handleLoginSuccess = (userData, accessToken) => {
    setUser(userData)
    setToken(accessToken)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setToken(null)
  }

  const fetchWithAuth = async (url, options = {}) => {
    const headers = {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    }
    return fetch(url, { ...options, headers })
  }

  const refreshStudents = async (nextQuery = query) => {
    if (!token) return
    setLoading(true)
    try {
      const response = await fetchWithAuth(`${API_URL}/students/search?q=${encodeURIComponent(nextQuery)}`)
      const data = await response.json()
      setStudents(data.items || [])
    } catch (error) {
      console.error('Failed to load students:', error)
      setStudents([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!token) return
    const timer = setTimeout(() => {
      refreshStudents(query)
    }, 150)
    return () => clearTimeout(timer)
  }, [query, token])

  const summary = useMemo(() => {
    return `${students.length} matching student${students.length === 1 ? '' : 's'}`
  }, [students])

  const handleApprove = async (studentId) => {
    await fetchWithAuth(`${API_URL}/students/approve?student_id=${encodeURIComponent(studentId)}`, {
      method: 'POST',
    })
    refreshStudents(query)
  }

  const handleHandoff = async (studentId) => {
    await fetchWithAuth(`${API_URL}/students/handoff?student_id=${encodeURIComponent(studentId)}`, {
      method: 'POST',
    })
    refreshStudents(query)
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    setLoading(true)
    setUploadResult(null)

    try {
      const response = await fetchWithAuth(`${API_URL}/students/upload`, {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()

      if (response.ok) {
        setUploadResult(result)
        // Refresh student data
        refreshStudents(query)
      } else {
        setUploadResult({
          error: true,
          message: result.detail || 'Upload failed',
        })
      }
    } catch (error) {
      setUploadResult({
        error: true,
        message: error.message || 'Upload failed',
      })
    } finally {
      setLoading(false)
      // Reset file input
      event.target.value = ''
    }
  }

  if (!user || !token) {
    return <Login onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">TTS_BDS</p>
          <h1>Distribution Desk</h1>
        </div>
        <div className="user-info">
          <span className="user-name">{user.username}</span>
          <span className="user-role">{user.role.replace('_', ' ')}</span>
          {user.assigned_grade && <span className="user-grade">{user.assigned_grade}</span>}
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      <section className="toolbar">
        <label className="search-box" htmlFor="student-search">
          <span>Search students</span>
          <input
            id="student-search"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Type sen, TTS-1001, school name..."
            autoComplete="off"
          />
        </label>
        <div className="summary">{loading ? 'Loading...' : summary}</div>
        {(user.role === 'admin' || user.role === 'books_team_lead') && (
          <button
            onClick={() => setShowUploadModal(true)}
            className="action-btn primary upload-btn"
          >
            📤 Upload Students
          </button>
        )}
      </section>

      {showUploadModal && (
        <div className="modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Upload Student Roster</h2>
              <button onClick={() => setShowUploadModal(false)} className="close-btn">×</button>
            </div>
            <div className="modal-body">
              <p className="upload-instructions">
                Upload a CSV or Excel file with student registration data.
                <br />
                <strong>Supports:</strong> CTA exports (.xls) and custom CSV files
                <br />
                <strong>CTA columns:</strong> Student ID, Student First Name, Student Last Name, Grade Name
                <br />
                <strong>Custom columns:</strong> cta_student_id, full_name, registered_grade_level
              </p>
              <label htmlFor="file-upload" className="file-upload-label">
                <input
                  id="file-upload"
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                  disabled={loading}
                />
                <span className="file-upload-btn">{loading ? 'Uploading...' : 'Choose File'}</span>
              </label>
              {loading && !uploadResult && (
                <div className="upload-loading">
                  <p>⏳ Processing file...</p>
                </div>
              )}
              {uploadResult && (
                <div className={`upload-result ${uploadResult.error ? 'upload-error' : 'upload-success'}`}>
                  {uploadResult.error ? (
                    <>
                      <h3>❌ Upload Failed</h3>
                      <p>{uploadResult.message}</p>
                    </>
                  ) : (
                    <>
                      <h3>✅ Upload Complete</h3>
                      <div className="upload-summary">
                        <p><strong>Total rows:</strong> {uploadResult.summary?.total_rows || 0}</p>
                        <p><strong>Inserted:</strong> {uploadResult.summary?.inserted || 0}</p>
                        <p><strong>Updated:</strong> {uploadResult.summary?.updated || 0}</p>
                        <p><strong>Errors:</strong> {uploadResult.summary?.errors || 0}</p>
                      </div>
                      {uploadResult.error_details && uploadResult.error_details.length > 0 && (
                        <div className="error-details">
                          <h4>Error Details:</h4>
                          <ul>
                            {uploadResult.error_details.map((error, idx) => (
                              <li key={idx}>{error}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <section className="panel-grid">
        <div className="panel table-card">
          <div className="panel-header">
            <h2>Student Search</h2>
          </div>
          <div className="scrollable-content">
            <table>
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {students.length === 0 ? (
                <tr>
                  <td colSpan="5" className="empty-state">
                    {query ? 'No matching students found.' : 'Start typing to filter students.'}
                  </td>
                </tr>
              ) : (
                students.map((student) => (
                  <tr key={student.id}>
                    <td>{student.cta_student_id}</td>
                    <td>
                      {student.name}
                      {student.section && <small className="section-badge"> [{student.section}]</small>}
                    </td>
                    <td>{student.email}</td>
                    <td>
                      <span className={`status ${STATUS_CLASS[student.status] || 'status-default'}`}>
                        {STATUS_TEXT[student.status] || student.status}
                      </span>
                    </td>
                    <td>
                      {student.status === 'READY_FOR_PICKUP' || student.status === 'PENDING_SWAP' ? (
                        <button type="button" className="action-btn primary" onClick={() => handleApprove(student.id)}>
                          Approve
                        </button>
                      ) : student.status === 'APPROVED' ? (
                        <button type="button" className="action-btn success" onClick={() => handleHandoff(student.id)}>
                          Handoff
                        </button>
                      ) : (
                        <span className="small-muted">Done</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          </div>
        </div>
      </section>
    </div>
  )
}

export default App

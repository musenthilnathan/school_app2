import { useCallback, useEffect, useState } from 'react'
import './BookInventories.css'

export default function BookInventories({ apiUrl, token, user }) {
  const canEdit = user.role === 'admin' || user.role === 'books_team_lead'

  const [data, setData] = useState({ items: [], grade_levels: [], total_complete_sets: 0, total_extra: 0 })
  const [grade, setGrade] = useState('')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [drafts, setDrafts] = useState({}) // { [id]: { complete_set_count, extra_count } }
  const [savingId, setSavingId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (grade) params.set('grade_level', grade)
      if (query.trim()) params.set('q', query.trim())
      const res = await fetch(`${apiUrl}/book-inventories?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`Failed to load (${res.status})`)
      setData(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [apiUrl, token, grade, query])

  useEffect(() => {
    const timer = setTimeout(load, 150)
    return () => clearTimeout(timer)
  }, [load])

  const setDraft = (item, field, value) => {
    setDrafts((prev) => ({
      ...prev,
      [item.id]: {
        complete_set_count: item.complete_set_count,
        extra_count: item.extra_count,
        ...prev[item.id],
        [field]: value,
      },
    }))
  }

  const cancel = (id) =>
    setDrafts((prev) => {
      const next = { ...prev }
      delete next[id]
      return next
    })

  const save = async (id) => {
    const d = drafts[id]
    const body = {
      complete_set_count: Number(d.complete_set_count),
      extra_count: Number(d.extra_count),
    }
    if (Object.values(body).some((n) => !Number.isInteger(n) || n < 0)) {
      setError('Counts must be whole numbers, 0 or more.')
      return
    }
    setSavingId(id)
    setError('')
    try {
      const res = await fetch(`${apiUrl}/book-inventories/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Save failed (${res.status})`)
      }
      cancel(id)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setSavingId(null)
    }
  }

  return (
    <>
      <section className="toolbar">
        <label className="search-box" htmlFor="inv-search">
          <span>Search category</span>
          <input
            id="inv-search"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Textbook, Handwriting, Unit 1..."
            autoComplete="off"
          />
        </label>
        <label className="search-box inv-grade" htmlFor="inv-grade">
          <span>Grade level</span>
          <select id="inv-grade" value={grade} onChange={(e) => setGrade(e.target.value)}>
            <option value="">All grades</option>
            {data.grade_levels.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </label>
        <div className="summary">{loading ? 'Loading...' : `${data.total} book${data.total === 1 ? '' : 's'}`}</div>
      </section>

      <section className="inv-cards">
        <div className="inv-card"><span>Titles</span><strong>{data.total}</strong></div>
        <div className="inv-card"><span>Complete sets</span><strong>{data.total_complete_sets}</strong></div>
        <div className="inv-card"><span>Extra</span><strong>{data.total_extra}</strong></div>
      </section>

      {error && <div className="inv-error">{error}</div>}

      <section className="panel-grid">
        <div className="panel table-card">
          <div className="panel-header">
            <h2>Book Inventory</h2>
          </div>
          <div className="scrollable-content">
            <table>
              <thead>
                <tr>
                  <th>Grade Level</th>
                  <th>Category</th>
                  <th>Complete Set Count</th>
                  <th>Extra Count</th>
                  {canEdit && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 ? (
                  <tr>
                    <td colSpan={canEdit ? 5 : 4} className="empty-state">
                      {loading ? 'Loading...' : 'No book inventory found.'}
                    </td>
                  </tr>
                ) : (
                  data.items.map((item) => {
                    const d = drafts[item.id]
                    return (
                      <tr key={item.id}>
                        <td>{item.grade_level}</td>
                        <td>{item.category}</td>
                        <td>
                          {canEdit && d ? (
                            <input
                              className="inv-num"
                              type="number"
                              min="0"
                              value={d.complete_set_count}
                              onChange={(e) => setDraft(item, 'complete_set_count', e.target.value)}
                            />
                          ) : (
                            item.complete_set_count
                          )}
                        </td>
                        <td>
                          {canEdit && d ? (
                            <input
                              className="inv-num"
                              type="number"
                              min="0"
                              value={d.extra_count}
                              onChange={(e) => setDraft(item, 'extra_count', e.target.value)}
                            />
                          ) : (
                            item.extra_count
                          )}
                        </td>
                        {canEdit && (
                          <td>
                            {d ? (
                              <>
                                <button
                                  type="button"
                                  className="action-btn success"
                                  disabled={savingId === item.id}
                                  onClick={() => save(item.id)}
                                >
                                  {savingId === item.id ? 'Saving...' : 'Save'}
                                </button>{' '}
                                <button type="button" className="action-btn secondary" onClick={() => cancel(item.id)}>
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <button type="button" className="action-btn primary" onClick={() => setDraft(item, 'complete_set_count', item.complete_set_count)}>
                                Edit
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  )
}

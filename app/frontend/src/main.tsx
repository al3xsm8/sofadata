import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

type TeamStatistics = {
  team_id: number
  team_name: string
  is_home: boolean
  goals: number | null
  half_time_goals: number | null
  second_half_goals: number | null
  result: string | null
  half_time_result: string | null
  second_half_result: string | null
  corners: number | null
  half_time_corners: number | null
  second_half_corners: number | null
  cards_total: number | null
  half_time_cards_total: number | null
  second_half_cards_total: number | null
  shots: number | null
  half_time_shots: number | null
  second_half_shots: number | null
  shots_on_target: number | null
  half_time_shots_on_target: number | null
  second_half_shots_on_target: number | null
}

type Match = {
  id: number
  source_id: number
  match_date: string
  status: string | null
  round: number | null
  season_source_id: number | null
  competition: string | null
  home_team: string
  away_team: string
  home_goals: number | null
  away_goals: number | null
  home_half_time_goals: number | null
  away_half_time_goals: number | null
  home_second_half_goals: number | null
  away_second_half_goals: number | null
  team_statistics: TeamStatistics[]
  analysis: MatchAnalysis | null
}

type TeamAverage = {
  team_id: number
  team_name: string
  matches_used: number
  window: string
  goals: number | null
  corners: number | null
  cards_total: number | null
  shots: number | null
  shots_on_target: number | null
}

type Meeting = {
  match_date: string
  home_team: string
  away_team: string
  home_goals: number | null
  away_goals: number | null
}

type MatchAnalysis = {
  window: string
  limit: number | null
  season_source_id: number | null
  averages: TeamAverage[]
  head_to_head: {
    matches_used: number
    home_wins: number
    draws: number
    away_wins: number
    meetings: Meeting[]
  }
}

type MatchPage = { items: Match[]; total: number; limit: number; offset: number }
type MatchSnapshot = { schema_version: number; generated_at: string; total: number; items: Match[] }
type TeamOption = { id: number; name: string }
type Filters = {
  from: string
  to: string
  competition: string
  team: string
  opponent: string
  venue: string
  round: string
  status: string
}

const columns = [
  ['date', 'Data', false], ['competition', 'Campeonato', false], ['ord', 'Ord', true], ['team', 'Time', true], ['opponent', 'Adversario', true], ['venue', 'Local', true], ['round', 'Rodada', true],
  ['score', 'Placar', true], ['result', 'Resultado', true],
  ['halfScore', 'Placar 1ºt', true], ['halfResult', 'Resultado 1ºt', true], ['secondScore', 'Placar 2ºt', true],
  ['secondResult', 'Resultado 2ºt', true], ['goals', 'Gol', true], ['halfGoals', 'Gol 1ºt', true], ['secondGoals', 'Gol 2ºt', true],
  ['corners', 'Escanteios', true], ['cards', 'Cartões', true], ['shots', 'Chutes', true], ['shotsOnTarget', 'Chutes no Gol', true],
  ['halfCorners', 'Escanteios 1ºt', true], ['halfCards', 'Cartões 1ºt', true], ['halfShots', 'Chutes 1ºt', true],
  ['halfShotsOnTarget', 'Chutes no Gol 1ºt', true], ['secondCorners', 'Escanteios 2ºt', true], ['secondCards', 'Cartões 2ºt', true],
  ['secondShots', 'Chutes 2ºt', true], ['secondShotsOnTarget', 'Chutes no Gol 2ºt', true],
] as const
type ColumnKey = (typeof columns)[number][0]
const defaultColumns: ColumnKey[] = columns.filter(([, , defaultVisible]) => defaultVisible !== false).map(([key]) => key)

const emptyFilters: Filters = {
  from: '', to: '', competition: '', team: '', opponent: '', venue: '', round: '', status: '',
}

const dataUrl = import.meta.env.VITE_DATA_URL || `${import.meta.env.BASE_URL}data/matches.json`
const cacheKey = 'sofadata-public-matches-v1'
const staticDataMode = import.meta.env.VITE_STATIC_DATA === 'true'

function extractTeams(items: Match[]): TeamOption[] {
  const teams = new Map<number, string>()
  items.forEach(match => match.team_statistics.forEach(stat => teams.set(stat.team_id, stat.team_name)))
  return [...teams].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))
}

function filterMatches(items: Match[], filters: Filters): Match[] {
  const query = filters.competition.trim().toLocaleLowerCase('pt-BR')
  return items.filter(match => {
    const matchDay = match.match_date.slice(0, 10)
    if (filters.from && matchDay < filters.from) return false
    if (filters.to && matchDay > filters.to) return false
    if (query && !(match.competition ?? '').toLocaleLowerCase('pt-BR').includes(query)) return false
    if (filters.round && match.round !== Number(filters.round)) return false
    if (filters.status && match.status !== filters.status) return false
    const teamStat = filters.team
      ? match.team_statistics.find(stat => String(stat.team_id) === filters.team)
      : undefined
    if (filters.team && !teamStat) return false
    if (filters.opponent && !match.team_statistics.some(stat => String(stat.team_id) === filters.opponent && stat.team_id !== teamStat?.team_id)) return false
    if (filters.venue === 'home' && teamStat && !teamStat.is_home) return false
    if (filters.venue === 'away' && teamStat && teamStat.is_home) return false
    return true
  })
}

function value(value: number | null | undefined) {
  return value ?? '—'
}

function localDate(iso: string) {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(new Date(iso))
}

function App() {
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [matches, setMatches] = useState<Match[]>([])
  const [teams, setTeams] = useState<TeamOption[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<Match | null>(null)
  const [analysisWindow, setAnalysisWindow] = useState<'last_n' | 'season'>('last_n')
  const [analysisN, setAnalysisN] = useState(10)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [visibleColumns, setVisibleColumns] = useState<ColumnKey[]>(() => {
    try {
      const saved = localStorage.getItem('sofadata-visible-columns')
      return saved ? JSON.parse(saved) as ColumnKey[] : defaultColumns
    } catch { return defaultColumns }
  })
  const [customizeOpen, setCustomizeOpen] = useState(false)
  const [sortKey, setSortKey] = useState<ColumnKey>('date')
  const [sortAscending, setSortAscending] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [snapshot, setSnapshot] = useState<MatchSnapshot | null>(null)
  const [updatingData, setUpdatingData] = useState(false)
  const [dataMessage, setDataMessage] = useState('')
  const pageSize = 20

  useEffect(() => {
    try {
      const cached = localStorage.getItem(cacheKey)
      if (cached) {
        const parsed = JSON.parse(cached) as MatchSnapshot
        if (parsed.schema_version === 1 && Array.isArray(parsed.items)) {
          setSnapshot(parsed)
          setTeams(extractTeams(parsed.items))
        }
      }
    } catch {
      localStorage.removeItem(cacheKey)
    }
    void refreshSnapshot(false)
  }, [])

  async function refreshSnapshot(showErrors = true) {
    setUpdatingData(true)
    setDataMessage('')
    try {
      const separator = dataUrl.includes('?') ? '&' : '?'
      const response = await fetch(`${dataUrl}${separator}_=${Date.now()}`, { cache: 'no-store' })
      if (!response.ok) throw new Error(`Não foi possível baixar os dados (${response.status}).`)
      const result = await response.json() as MatchSnapshot
      if (result.schema_version !== 1 || !Array.isArray(result.items)) throw new Error('O arquivo JSON tem um formato inválido.')
      setSnapshot(result)
      setTeams(extractTeams(result.items))
      setPage(0)
      localStorage.setItem(cacheKey, JSON.stringify(result))
      setDataMessage(`Dados atualizados: ${result.total} partidas.`)
    } catch (reason) {
      if (showErrors) setError(reason instanceof Error ? reason.message : 'Falha ao atualizar os dados.')
      else if (!snapshot) {
        try {
          if (staticDataMode) throw new Error('O JSON público não respondeu.')
          const localResponse = await fetch('/api/data/matches.json', { cache: 'no-store' })
          if (!localResponse.ok) throw new Error()
          const localSnapshot = await localResponse.json() as MatchSnapshot
          setSnapshot(localSnapshot)
          setTeams(extractTeams(localSnapshot.items))
          localStorage.setItem(cacheKey, JSON.stringify(localSnapshot))
          setDataMessage(`Dados locais carregados: ${localSnapshot.total} partidas. Publique data/matches.json para o GitHub Pages.`)
        } catch {
          setError('Não foi possível carregar o JSON. Publique data/matches.json ou inicie o backend local.')
        }
      }
    } finally {
      setUpdatingData(false)
    }
  }

  useEffect(() => {
    if (!snapshot) return
    const filtered = filterMatches(snapshot.items, filters)
    setTotal(filtered.length)
    setMatches(filtered.slice(page * pageSize, (page + 1) * pageSize))
  }, [filters, page, snapshot])

  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const orderedMatches = useMemo(() => [...matches].sort((a,b)=>{
    const getValue=(match:Match):string|number=>{
      if(sortKey==='date') return match.match_date
      if(sortKey==='competition') return match.competition??''
      if(sortKey==='ord') return match.round??-1
      if(sortKey==='round') return match.round??-1
      if(sortKey==='score') return (match.home_goals??-1)-(match.away_goals??-1)
      return match.home_team
    }
    const av=getValue(a),bv=getValue(b)
    const cmp=typeof av==='number'&&typeof bv==='number'?av-bv:String(av).localeCompare(String(bv),'pt-BR')
    return sortAscending?cmp:-cmp
  }),[matches,sortKey,sortAscending])
  const summary = useMemo(() => `${total} ${total === 1 ? 'partida encontrada' : 'partidas encontradas'}`, [total])

  function update<K extends keyof Filters>(key: K, next: Filters[K]) {
    setFilters(current => ({ ...current, [key]: next }))
    setPage(0)
  }

  function toggleColumn(key: ColumnKey) {
    const next = visibleColumns.includes(key) ? visibleColumns.filter(item => item !== key) : [...visibleColumns, key]
    setVisibleColumns(next)
    localStorage.setItem('sofadata-visible-columns', JSON.stringify(next))
  }

  async function exportExcel() {
    if (staticDataMode) {
      setError('A exportação Excel ainda requer o backend local; no GitHub Pages você pode consultar e filtrar os dados JSON.')
      return
    }
    setExporting(true)
    try {
      const form = document.querySelector<HTMLFormElement>('.filter-panel form')
      const values = form ? new FormData(form) : null
      const current = (key: keyof Filters) => values?.get(key)?.toString().trim() ?? filters[key].trim()
      const currentFilters = { ...filters }
      ;(Object.keys(currentFilters) as (keyof Filters)[]).forEach(key => { currentFilters[key] = current(key) })
      const selectedMatches = filterMatches(snapshot?.items ?? [], currentFilters)
      const rows: (string | number | null)[][] = []
      selectedMatches.forEach((match, matchIndex) => {
        for (const stat of [...match.team_statistics].sort((a, b) => Number(b.is_home) - Number(a.is_home))) {
          rows.push([
            localDate(match.match_date), match.competition, matchIndex + 1, stat.team_name,
            stat.is_home ? match.away_team : match.home_team, stat.is_home ? 'Casa' : 'Fora', match.round,
            `${value(match.home_goals)} - ${value(match.away_goals)}`, stat.result,
            `${value(match.home_half_time_goals)} - ${value(match.away_half_time_goals)}`, stat.half_time_result,
            `${value(match.home_second_half_goals)} - ${value(match.away_second_half_goals)}`, stat.second_half_result,
            stat.goals, stat.half_time_goals, stat.second_half_goals, stat.corners, stat.cards_total,
            stat.shots, stat.shots_on_target, stat.half_time_corners, stat.half_time_cards_total,
            stat.half_time_shots, stat.half_time_shots_on_target, stat.second_half_corners,
            stat.second_half_cards_total, stat.second_half_shots, stat.second_half_shots_on_target,
          ])
        }
      })
      const params = new URLSearchParams()
      if (current('from')) params.set('from', current('from'))
      if (current('to')) params.set('to', current('to'))
      if (current('competition')) params.set('competition', current('competition'))
      if (current('team')) params.set('team_id', current('team'))
      if (current('opponent')) params.set('opponent_id', current('opponent'))
      if (current('venue') === 'home') params.set('is_home', 'true')
      if (current('venue') === 'away') params.set('is_home', 'false')
      if (current('round')) params.set('round', current('round'))
      if (current('status')) params.set('status', current('status'))
      const response = await fetch(`/api/matches/export.xlsx?${params}`)
      if (!response.ok) throw new Error('Exportar Excel requer o backend local; no GitHub Pages use Baixar JSON para dados.')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'sofadata-partidas.xlsx'
      link.click()
      URL.revokeObjectURL(url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Falha ao exportar Excel.')
    } finally {
      setExporting(false)
    }
  }

  function rowValue(match: Match, stat: TeamStatistics, key: ColumnKey): string | number {
    const opponent = stat.is_home ? match.away_team : match.home_team
    const opposite = (home: number | null, away: number | null) => stat.is_home ? home : away
    const score = (home: number | null, away: number | null) => `${value(home)} - ${value(away)}`
    switch (key) {
      case 'ord': return ''
      case 'date': return localDate(match.match_date)
      case 'competition': return match.competition ?? '—'
      case 'team': return stat.team_name
      case 'opponent': return opponent
      case 'venue': return stat.is_home ? 'Casa' : 'Fora'
      case 'round': return value(match.round)
      case 'score': return score(match.home_goals, match.away_goals)
      case 'result': return stat.result ?? '—'
      case 'halfScore': return score(match.home_half_time_goals, match.away_half_time_goals)
      case 'halfResult': return stat.half_time_result ?? '—'
      case 'secondScore': return score(match.home_second_half_goals, match.away_second_half_goals)
      case 'secondResult': return stat.second_half_result ?? '—'
      case 'goals': return value(stat.goals)
      case 'halfGoals': return value(stat.half_time_goals)
      case 'secondGoals': return value(stat.second_half_goals)
      case 'corners': return value(stat.corners)
      case 'cards': return value(stat.cards_total)
      case 'shots': return value(stat.shots)
      case 'shotsOnTarget': return value(stat.shots_on_target)
      case 'halfCorners': return value(stat.half_time_corners)
      case 'halfCards': return value(stat.half_time_cards_total)
      case 'halfShots': return value(stat.half_time_shots)
      case 'halfShotsOnTarget': return value(stat.half_time_shots_on_target)
      case 'secondCorners': return value(stat.second_half_corners)
      case 'secondCards': return value(stat.second_half_cards_total)
      case 'secondShots': return value(stat.second_half_shots)
      case 'secondShotsOnTarget': return value(stat.second_half_shots_on_target)
      default: return String(opposite(match.home_goals, match.away_goals) ?? '—')
    }
  }

  async function openDetails(match: Match) {
    if (staticDataMode) {
      setSelected({ ...match, analysis: match.analysis ?? null })
      return
    }
    try {
      setAnalysisLoading(true)
      const response = await fetch(detailUrl(match.id, analysisWindow, analysisN))
      if (!response.ok) throw new Error('Não foi possível carregar os detalhes.')
      setSelected(await response.json() as Match)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível carregar os detalhes.')
    } finally {
      setAnalysisLoading(false)
    }
  }

  function detailUrl(matchId: number, window: 'last_n' | 'season', n: number) {
    const params = new URLSearchParams({ window })
    if (window === 'last_n') params.set('n', String(n))
    return `/api/matches/${matchId}?${params.toString()}`
  }

  async function refreshAnalysis() {
    if (!selected) return
    if (staticDataMode) {
      setError('Análises de médias e confrontos ainda não estão incluídas no JSON publicado.')
      return
    }
    setAnalysisLoading(true)
    try {
      const response = await fetch(detailUrl(selected.id, analysisWindow, analysisN))
      if (!response.ok) throw new Error('Não foi possível atualizar a análise.')
      setSelected(await response.json() as Match)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível atualizar a análise.')
    } finally {
      setAnalysisLoading(false)
    }
  }

  async function changeAnalysisWindow(next: 'last_n' | 'season') {
    setAnalysisWindow(next)
    if (!selected) return
    if (staticDataMode) return
    setAnalysisLoading(true)
    try {
      const response = await fetch(detailUrl(selected.id, next, analysisN))
      if (!response.ok) throw new Error('Não foi possível atualizar a análise.')
      setSelected(await response.json() as Match)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível atualizar a análise.')
    } finally {
      setAnalysisLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" aria-label="Sofadata início">
          <span className="brand-mark">S</span><span>Sofadata</span>
        </a>
        <span className="topbar-label">Estatísticas de partidas</span>
        <button className="refresh-data-button" type="button" onClick={() => void refreshSnapshot()} disabled={updatingData}>
          {updatingData ? 'Atualizando…' : 'Atualizar dados'}
        </button>
      </header>

      <section className="page-heading">
        <div>
          <p className="eyebrow">ACERVO DE JOGOS</p>
          <h1>Partidas</h1>
          <p className="subtitle">Consulte resultados e estatísticas por equipe.</p>
        </div>
        <div className="heading-actions"><div className="match-count"><strong>{total}</strong><span>partidas</span></div><button className="table-settings" aria-label="Personalizar tabela" onClick={()=>setCustomizeOpen(true)}>⚙</button></div>
      </section>

      <section className="filter-panel" aria-label="Filtros de partidas">
        <form onSubmit={event => event.preventDefault()}>
        <div className="filter-grid">
          <label>Data inicial<input name="from" type="date" value={filters.from} onChange={e => update('from', e.target.value)} /></label>
          <label>Data final<input name="to" type="date" value={filters.to} onChange={e => update('to', e.target.value)} /></label>
          <label className="wide-field">Campeonato<input name="competition" placeholder="Ex.: Premier League" value={filters.competition} onChange={e => update('competition', e.target.value)} /></label>
          <label>Time<select name="team" value={filters.team} onChange={e => {update('team',e.target.value);if(!e.target.value)update('opponent','')}}><option value="">Todos</option>{teams.map(team=><option key={team.id} value={team.id}>{team.name}</option>)}</select></label>
          <label>Adversário<select name="opponent" value={filters.opponent} onChange={e => update('opponent',e.target.value)} disabled={!filters.team}><option value="">Todos</option>{teams.filter(team=>String(team.id)!==filters.team).map(team=><option key={team.id} value={team.id}>{team.name}</option>)}</select></label>
          <label>Local<select name="venue" value={filters.venue} onChange={e => update('venue', e.target.value)}><option value="">Todos</option><option value="home">Casa</option><option value="away">Fora</option></select></label>
          <label>Rodada<input name="round" type="number" min="1" placeholder="Todas" value={filters.round} onChange={e => update('round', e.target.value)} /></label>
          <label>Status<select name="status" value={filters.status} onChange={e => update('status', e.target.value)}><option value="">Todos</option><option value="completed">Finalizada</option><option value="live">Ao vivo</option><option value="not_started">Não iniciada</option><option value="void">Cancelada/adiada</option></select></label>
          <button type="button" className="clear-button" onClick={() => { setFilters(emptyFilters); setPage(0) }}>Limpar filtros</button>
        </div>
        </form>
      </section>

      <div className="results-line"><span>{summary}{snapshot?.generated_at ? ` · JSON de ${localDate(snapshot.generated_at)}` : ''}{dataMessage ? ` · ${dataMessage}` : ''}</span><span>Datas exibidas no seu horário local <button className="export-button" onClick={()=>void exportExcel()} disabled={exporting||total===0}>{exporting?'Exportando…':'Exportar Excel'}</button></span></div>

      {error && <div className="notice error-notice" role="alert">{error}</div>}
      {loading && <div className="notice">Carregando partidas…</div>}
      {!loading && !error && matches.length === 0 && <div className="empty-state"><span className="empty-icon">⌕</span><h2>Nenhuma partida encontrada</h2><p>Tente ajustar os filtros ou importe partidas pelo backend.</p></div>}

      {!loading && matches.length > 0 && <section className="table-wrap" aria-label="Resultados das partidas">
        <table className="matches-table"><thead><tr>{columns.filter(([key])=>visibleColumns.includes(key)).map(([key,label])=><th key={key} onClick={()=>{if(['date','competition','team','round','score','ord'].includes(key)){if(sortKey===key)setSortAscending(!sortAscending);else{setSortKey(key);setSortAscending(true)}}}}>{label}{['date','competition','team','round','score','ord'].includes(key)&&<span className="sort-mark">{sortKey===key?(sortAscending?'↑':'↓'):'↕'}</span>}</th>)}<th className="action-head">⋮</th></tr></thead>
          {orderedMatches.map((match,matchIndex)=><tbody key={match.id} className="match-group">{[...match.team_statistics].sort((a,b)=>Number(b.is_home)-Number(a.is_home)).map(stat=><tr key={stat.team_id} className="team-row" onClick={()=>void openDetails(match)}>
            {columns.filter(([key])=>visibleColumns.includes(key)).map(([key])=><td key={key} className={key==='team'?'team-cell':key==='result'||key==='halfResult'||key==='secondResult'?'result-cell':''}>{key==='ord'?page*pageSize+matchIndex+1:rowValue(match,stat,key)}</td>)}
            <td><button className="row-details" aria-label={`Detalhes de ${stat.team_name}`} onClick={e=>{e.stopPropagation();void openDetails(match)}}>⋮</button></td>
          </tr>)}</tbody>)}
        </table>
      </section>}

      {total > pageSize && <nav className="pagination" aria-label="Paginação">
        <button disabled={page === 0} onClick={() => setPage(page - 1)}>← Anterior</button>
        <span>Página {page + 1} de {pageCount}</span>
        <button disabled={page + 1 >= pageCount} onClick={() => setPage(page + 1)}>Próxima →</button>
      </nav>}

      {selected && <div className="modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) setSelected(null) }}>
        <section className="details-modal" role="dialog" aria-modal="true" aria-labelledby="detail-title">
          <button className="close-button" aria-label="Fechar detalhes" onClick={() => setSelected(null)}>×</button>
          <p className="eyebrow">{selected.competition ?? 'PARTIDA'}</p>
          <h2 id="detail-title">{selected.home_team} <span>{value(selected.home_goals)} : {value(selected.away_goals)}</span> {selected.away_team}</h2>
          <p className="detail-date">{localDate(selected.match_date)} · Intervalo {value(selected.home_half_time_goals)} : {value(selected.away_half_time_goals)}</p>
          <div className="stats-table-wrap"><table className="stats-table"><thead><tr><th>Estatística</th><th>{selected.home_team} · Casa</th><th>{selected.away_team} · Fora</th></tr></thead><tbody>
            {([
              ['Gols', 'goals'], ['Gols 1º tempo', 'half_time_goals'], ['Gols 2º tempo', 'second_half_goals'], ['Escanteios', 'corners'], ['Escanteios 1º tempo', 'half_time_corners'], ['Escanteios 2º tempo', 'second_half_corners'], ['Cartões', 'cards_total'], ['Cartões 1º tempo', 'half_time_cards_total'], ['Cartões 2º tempo', 'second_half_cards_total'], ['Chutes', 'shots'], ['Chutes 1º tempo', 'half_time_shots'], ['Chutes 2º tempo', 'second_half_shots'], ['Chutes no gol', 'shots_on_target'], ['Chutes no gol 1º tempo', 'half_time_shots_on_target'], ['Chutes no gol 2º tempo', 'second_half_shots_on_target'],
            ] as const).map(([label, key]) => <tr key={key}><th>{label}</th><td>{value(selected.team_statistics.find(row => row.is_home)?.[key])}</td><td>{value(selected.team_statistics.find(row => !row.is_home)?.[key])}</td></tr>)}
          </tbody></table></div>
          <p className="data-note">“—” indica estatística não fornecida pela fonte.</p>

          <section className="analysis-section" aria-label="Médias das equipes">
            <div className="analysis-heading"><div><p className="eyebrow">DESEMPENHO ANTERIOR</p><h3>Médias por partida</h3></div>
              <div className="analysis-controls"><select aria-label="Janela das médias" value={analysisWindow} onChange={e => void changeAnalysisWindow(e.target.value as 'last_n'|'season')}><option value="last_n">Últimos jogos</option><option value="season">Temporada</option></select>
                {analysisWindow==='last_n'&&<><input aria-label="Quantidade de jogos" type="number" min="1" max="50" value={analysisN} onChange={e=>setAnalysisN(Math.max(1,Math.min(50,Number(e.target.value)||1)))}/><button className="details-button" onClick={()=>void refreshAnalysis()} disabled={analysisLoading}>{analysisLoading?'Atualizando…':'Atualizar análise'}</button></>}</div></div>
            <div className="stats-table-wrap"><table className="stats-table"><thead><tr><th>Média</th><th>{selected.home_team}</th><th>{selected.away_team}</th></tr></thead><tbody>
              {([
                ['Jogos usados', 'matches_used'], ['Gols', 'goals'], ['Escanteios', 'corners'], ['Cartões', 'cards_total'], ['Chutes', 'shots'], ['Chutes no gol', 'shots_on_target'],
              ] as const).map(([label,key])=><tr key={key}><th>{label}</th><td>{key==='matches_used'?value(selected.analysis?.averages.find(row=>row.team_id===selected.team_statistics.find(s=>s.is_home)?.team_id)?.[key]):value(selected.analysis?.averages.find(row=>row.team_id===selected.team_statistics.find(s=>s.is_home)?.team_id)?.[key])}</td><td>{key==='matches_used'?value(selected.analysis?.averages.find(row=>row.team_id===selected.team_statistics.find(s=>!s.is_home)?.team_id)?.[key]):value(selected.analysis?.averages.find(row=>row.team_id===selected.team_statistics.find(s=>!s.is_home)?.team_id)?.[key])}</td></tr>)}
            </tbody></table></div>
            {staticDataMode && !selected.analysis && <p className="data-note">As médias ainda não estão incluídas no JSON publicado.</p>}
          </section>

          <section className="analysis-section" aria-label="Confrontos diretos">
            <div className="analysis-heading"><div><p className="eyebrow">HISTÓRICO</p><h3>Confrontos diretos</h3><p className="data-note">Mesma competição e temporada · {selected.analysis?.head_to_head.matches_used ?? 0} jogo(s)</p></div><div className="h2h-score">{selected.analysis?.head_to_head.home_wins ?? 0} <small>V</small> · {selected.analysis?.head_to_head.draws ?? 0} <small>E</small> · {selected.analysis?.head_to_head.away_wins ?? 0} <small>V</small></div></div>
            {selected.analysis?.head_to_head.meetings.length ? <div className="meeting-list">{selected.analysis.head_to_head.meetings.map((meeting,index)=><div className="meeting-row" key={`${meeting.match_date}-${index}`}><span>{localDate(meeting.match_date)}</span><strong>{meeting.home_team} {value(meeting.home_goals)} : {value(meeting.away_goals)} {meeting.away_team}</strong></div>)}</div> : <p className="data-note">{staticDataMode ? 'Os confrontos diretos ainda não estão incluídos no JSON publicado.' : 'Não há confrontos anteriores armazenados nesta competição e temporada.'}</p>}
          </section>
        </section>
      </div>}

      {customizeOpen&&<div className="modal-backdrop settings-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setCustomizeOpen(false)}}><section className="column-modal" role="dialog" aria-modal="true" aria-labelledby="columns-title"><h2 id="columns-title">Personalizar tabela</h2><div className="column-options">{columns.map(([key,label])=><label key={key}><input type="checkbox" checked={visibleColumns.includes(key)} onChange={()=>toggleColumn(key)}/><span>{label}</span></label>)}</div><button className="modal-close-link" onClick={()=>setCustomizeOpen(false)}>Fechar</button></section></div>}

      <footer>SOFADATA <span>·</span> Fonte não oficial · Dados sujeitos à disponibilidade do SofaScore Scraper</footer>
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)

import React, { useState, useMemo } from 'react'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Collapse,
  IconButton,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Alert,
  Tooltip,
} from '@mui/material'
import {
  FlightTakeoff,
  School,
  TrendingUp,
  Schedule,
  LocationOn,
  Search,
  FilterList,
  ExpandMore,
  KeyboardArrowDown,
  KeyboardArrowUp,
  Error,
  Warning,
} from '@mui/icons-material'
import { LogbookData, LogbookEntry } from '../services/logbookService'

interface DashboardContentProps {
  logbookData: LogbookData
}

const DashboardContent: React.FC<DashboardContentProps> = ({ logbookData }) => {
  const [selectedTab, setSelectedTab] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [aircraftFilter, setAircraftFilter] = useState('')
  const [sortBy, setSortBy] = useState('date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  // Get unique aircraft for filter dropdown
  const uniqueAircraft = useMemo(() => {
    const aircraft = new Set(logbookData.entries.map(entry => entry.aircraft?.registration).filter(Boolean))
    return Array.from(aircraft).sort()
  }, [logbookData.entries])

  // Filter and sort entries
  const filteredEntries = useMemo(() => {
    let filtered = logbookData.entries.filter(entry => {
      const matchesSearch = !searchTerm || 
        entry.aircraft?.registration?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        entry.aircraft?.type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        entry.departure?.identifier?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        entry.destination?.identifier?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        entry.remarks?.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesAircraft = !aircraftFilter || entry.aircraft?.registration === aircraftFilter

      return matchesSearch && matchesAircraft
    })

    // Sort entries
    filtered.sort((a, b) => {
      let aValue: any, bValue: any
      
      switch (sortBy) {
        case 'date':
          aValue = new Date(a.date)
          bValue = new Date(b.date)
          break
        case 'aircraft':
          aValue = a.aircraft?.registration || ''
          bValue = b.aircraft?.registration || ''
          break
        case 'total_time':
          aValue = a.total_time || 0
          bValue = b.total_time || 0
          break
        case 'route':
          aValue = `${a.departure?.identifier || ''}-${a.destination?.identifier || ''}`
          bValue = `${b.departure?.identifier || ''}-${b.destination?.identifier || ''}`
          break
        default:
          aValue = a.date
          bValue = b.date
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

    return filtered
  }, [logbookData.entries, searchTerm, aircraftFilter, sortBy, sortOrder])

  const toggleRowExpansion = (index: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedRows(newExpanded)
  }

  const formatTime = (time: number | undefined): string => {
    if (time === undefined || time === null) return '0.0'
    return time.toFixed(1)
  }

  const formatDate = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return dateString
    }
  }

  const StatCard = ({ title, value, subtitle, icon, color = 'primary' }: {
    title: string
    value: string | number
    subtitle?: string
    icon: React.ReactNode
    color?: 'primary' | 'secondary' | 'success' | 'warning'
  }) => (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={1}>
          <Box color={`${color}.main`} mr={1}>
            {icon}
          </Box>
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" component="div" color={`${color}.main`}>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  )

  return (
    <Box>
      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Hours"
            value={formatTime(logbookData.stats?.total_time)}
            subtitle="Current Year"
            icon={<FlightTakeoff />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="PIC Hours"
            value={formatTime(logbookData.stats?.total_pic)}
            subtitle="Current Year"
            icon={<School />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Flights"
            value={logbookData.entries?.length || 0}
            subtitle="All Time"
            icon={<TrendingUp />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Night Hours"
            value={formatTime(logbookData.stats?.total_night)}
            subtitle="Current Year"
            icon={<Schedule />}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* All Time vs Current Year Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                All Time Totals
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Total Hours</Typography>
                  <Typography variant="h6">{formatTime(logbookData.all_time?.total_time)}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">PIC Hours</Typography>
                  <Typography variant="h6">{formatTime(logbookData.all_time?.total_pic)}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Cross Country</Typography>
                  <Typography variant="h6">{formatTime(logbookData.all_time?.total_cross_country)}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Night Hours</Typography>
                  <Typography variant="h6">{formatTime(logbookData.all_time?.total_night)}</Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Experience (30 days)
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Total Hours</Typography>
                  <Typography variant="h6">{formatTime(logbookData.recent_experience?.total_time)}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Landings</Typography>
                  <Typography variant="h6">{logbookData.recent_experience?.total_landings || 0}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Night Hours</Typography>
                  <Typography variant="h6">{formatTime(logbookData.recent_experience?.total_night)}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Cross Country</Typography>
                  <Typography variant="h6">{formatTime(logbookData.recent_experience?.total_cross_country)}</Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Logbook Entries */}
      <Card elevation={2}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h6">
              Logbook Entries ({filteredEntries.length})
            </Typography>
          </Box>

          {/* Error Summary */}
          {(() => {
            const errorEntries = filteredEntries.filter(entry => entry.error_explanation)
            if (errorEntries.length > 0) {
              return (
                <Alert severity="warning" sx={{ mb: 3 }}>
                  <Typography variant="body2">
                    <strong>{errorEntries.length}</strong> entries have validation issues. 
                    Invalid entries are highlighted in red with error details available when expanded.
                  </Typography>
                </Alert>
              )
            }
            return null
          })()}

          {/* Search and Filter Controls */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search flights..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Aircraft</InputLabel>
                <Select
                  value={aircraftFilter}
                  label="Aircraft"
                  onChange={(e) => setAircraftFilter(e.target.value)}
                >
                  <MenuItem value="">All Aircraft</MenuItem>
                  {uniqueAircraft.map((aircraft) => (
                    <MenuItem key={aircraft} value={aircraft}>
                      {aircraft}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Sort By</InputLabel>
                <Select
                  value={sortBy}
                  label="Sort By"
                  onChange={(e) => setSortBy(e.target.value)}
                >
                  <MenuItem value="date">Date</MenuItem>
                  <MenuItem value="aircraft">Aircraft</MenuItem>
                  <MenuItem value="total_time">Flight Time</MenuItem>
                  <MenuItem value="route">Route</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Order</InputLabel>
                <Select
                  value={sortOrder}
                  label="Order"
                  onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                >
                  <MenuItem value="desc">Newest First</MenuItem>
                  <MenuItem value="asc">Oldest First</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          {/* Entries Table */}
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell></TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Aircraft</TableCell>
                  <TableCell>Route</TableCell>
                  <TableCell align="right">Total Time</TableCell>
                  <TableCell align="right">PIC</TableCell>
                  <TableCell align="right">Dual</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell align="right">Landings</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredEntries.map((entry, index) => {
                  const hasError = entry.error_explanation !== null && entry.error_explanation !== undefined
                  return (
                  <React.Fragment key={index}>
                    <TableRow 
                      hover
                      sx={{
                        backgroundColor: hasError ? '#ffebee' : 'inherit',
                        '&:hover': {
                          backgroundColor: hasError ? '#ffcdd2' : 'rgba(0, 0, 0, 0.04)',
                        },
                      }}
                    >
                      <TableCell>
                        <Box display="flex" alignItems="center" gap={1}>
                          <IconButton
                            size="small"
                            onClick={() => toggleRowExpansion(index)}
                          >
                            {expandedRows.has(index) ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
                          </IconButton>
                          {hasError && (
                            <Tooltip title={entry.error_explanation || 'Invalid entry'}>
                              <Error color="error" fontSize="small" />
                            </Tooltip>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>{formatDate(entry.date)}</TableCell>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {entry.aircraft?.registration || 'N/A'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {entry.aircraft?.type || 'Unknown'}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box display="flex" alignItems="center" gap={1}>
                          <LocationOn fontSize="small" color="action" />
                          <Typography variant="body2">
                            {entry.departure?.identifier || '???'} → {entry.destination?.identifier || '???'}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="right">{formatTime(entry.total_time)}</TableCell>
                      <TableCell align="right">{formatTime(entry.pic_time)}</TableCell>
                      <TableCell align="right">{formatTime(entry.dual_received)}</TableCell>
                      <TableCell>
                        <Chip
                          label={entry.pilot_role || 'PIC'}
                          size="small"
                          color={entry.pilot_role === 'PIC' ? 'primary' : 'default'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        {(entry.landings_day || 0) + (entry.landings_night || 0)}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={9}>
                        <Collapse in={expandedRows.has(index)} timeout="auto" unmountOnExit>
                          <Box sx={{ margin: 1 }}>
                            <Grid container spacing={2}>
                              <Grid item xs={12} md={6}>
                                <Typography variant="subtitle2" gutterBottom>
                                  Flight Details
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Solo:</strong> {formatTime(entry.solo_time)} hrs
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Day Landings:</strong> {entry.landings_day || 0}
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Night Landings:</strong> {entry.landings_night || 0}
                                </Typography>
                              </Grid>
                              <Grid item xs={12} md={6}>
                                <Typography variant="subtitle2" gutterBottom>
                                  Conditions
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Day:</strong> {formatTime(entry.conditions?.day)} hrs
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Night:</strong> {formatTime(entry.conditions?.night)} hrs
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Cross Country:</strong> {formatTime(entry.conditions?.cross_country)} hrs
                                </Typography>
                              </Grid>
                              {entry.remarks && (
                                <Grid item xs={12}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    Remarks
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {entry.remarks}
                                  </Typography>
                                </Grid>
                              )}
                              {hasError && (
                                <Grid item xs={12}>
                                  <Alert severity="error" sx={{ mt: 1 }}>
                                    <Typography variant="subtitle2" gutterBottom>
                                      Data Validation Issues
                                    </Typography>
                                    <Typography variant="body2">
                                      {entry.error_explanation}
                                    </Typography>
                                  </Alert>
                                </Grid>
                              )}
                            </Grid>
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>

          {filteredEntries.length === 0 && (
            <Box textAlign="center" py={4}>
              <Typography variant="body1" color="text.secondary">
                No flights found matching your criteria.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}

export default DashboardContent

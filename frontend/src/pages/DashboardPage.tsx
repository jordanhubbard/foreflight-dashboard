import React, { useState, useEffect, useMemo } from 'react'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Checkbox,
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
} from '@mui/material'
import {
  FlightTakeoff,
  Upload,
  School,
  TrendingUp,
  Schedule,
  LocationOn,
  Add,
  Search,
  FilterList,
  ExpandMore,
  KeyboardArrowDown,
  KeyboardArrowUp,
  Sort,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material'
import { motion } from 'framer-motion'
import { useAuthStore } from '../hooks/useAuthStore'
import { authService, type LogbookData } from '../services/authService'
import toast from 'react-hot-toast'
import LoadingSpinner from '../components/LoadingSpinner'

const DashboardPage: React.FC = () => {
  const { user } = useAuthStore()
  const [logbookData, setLogbookData] = useState<LogbookData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isStudentPilot, setIsStudentPilot] = useState(user?.student_pilot || false)
  const [isUploading, setIsUploading] = useState(false)
  
  // Flight table state
  const [searchTerm, setSearchTerm] = useState('')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [filters, setFilters] = useState({
    all: true,
    pic: false,
    dual: false,
    solo: false,
    night: false,
    xc: false,
    instrument: false,
  })
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [showRunningTotals, setShowRunningTotals] = useState(false)
  const [currentTab, setCurrentTab] = useState(0)

  useEffect(() => {
    loadLogbookData()
  }, [])

  // Filtered and sorted entries
  const filteredEntries = useMemo(() => {
    if (!logbookData?.entries) return []
    
    let filtered = logbookData.entries.filter(entry => {
      // Search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase()
        const matchesSearch = 
          entry.aircraft.registration.toLowerCase().includes(searchLower) ||
          entry.aircraft.type.toLowerCase().includes(searchLower) ||
          entry.departure?.identifier?.toLowerCase().includes(searchLower) ||
          entry.destination?.identifier?.toLowerCase().includes(searchLower) ||
          entry.remarks?.toLowerCase().includes(searchLower)
        if (!matchesSearch) return false
      }
      
      // Type filters
      if (!filters.all) {
        const matchesFilter = 
          (filters.pic && entry.pic_time > 0) ||
          (filters.dual && entry.dual_received > 0) ||
          (filters.solo && entry.pic_time > 0 && entry.dual_received === 0) ||
          (filters.night && entry.conditions.night > 0) ||
          (filters.xc && entry.conditions.cross_country > 0) ||
          (filters.instrument && (entry.conditions.simulated_instrument > 0 || entry.conditions.actual_instrument > 0))
        if (!matchesFilter) return false
      }
      
      return true
    })
    
    // Sort by date
    filtered.sort((a, b) => {
      const dateA = new Date(a.date).getTime()
      const dateB = new Date(b.date).getTime()
      return sortOrder === 'desc' ? dateB - dateA : dateA - dateB
    })
    
    return filtered
  }, [logbookData?.entries, searchTerm, filters, sortOrder])

  // Helper functions
  const toggleRowExpansion = (index: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedRows(newExpanded)
  }

  const handleFilterChange = (filterType: keyof typeof filters) => {
    if (filterType === 'all') {
      setFilters({
        all: true,
        pic: false,
        dual: false,
        solo: false,
        night: false,
        xc: false,
        instrument: false,
      })
    } else {
      setFilters(prev => ({
        ...prev,
        all: false,
        [filterType]: !prev[filterType],
      }))
    }
  }

  const loadLogbookData = async () => {
    try {
      setIsLoading(true)
      const data = await authService.getLogbookData()
      setLogbookData(data)
    } catch (error) {
      console.error('Failed to load logbook data:', error)
      toast.error('Failed to load logbook data. Please try again.')
      // Set empty data to prevent UI crashes
      setLogbookData({
        entries: [],
        stats: { total_hours: 0, total_time: 0 },
        all_time_stats: { total_hours: 0, total_time: 0 },
        aircraft_stats: [],
        recent_experience: { total_hours: 0, total_time: 0 }
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async () => {
    if (!selectedFile) return

    try {
      setIsUploading(true)
      await authService.uploadLogbook(selectedFile, isStudentPilot)
      toast.success('Logbook uploaded successfully!')
      setUploadDialogOpen(false)
      setSelectedFile(null)
      await loadLogbookData()
    } catch (error: any) {
      toast.error(error.message || 'Failed to upload logbook')
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file && file.type === 'text/csv') {
      setSelectedFile(file)
    } else {
      toast.error('Please select a valid CSV file')
    }
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LoadingSpinner message="Loading your dashboard..." />
      </Box>
    )
  }

  const hasLogbookData = logbookData && logbookData.entries?.length > 0

  return (
    <Box>
      {/* Welcome Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box mb={4}>
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome back, {user?.first_name}!
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {hasLogbookData 
              ? 'Here\'s your latest flight data and statistics.'
              : 'Upload your ForeFlight logbook to get started with detailed flight analytics.'
            }
          </Typography>
        </Box>
      </motion.div>

      {!hasLogbookData ? (
        /* Empty State */
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Card sx={{ textAlign: 'center', py: 6 }}>
            <CardContent>
              <Box
                sx={{
                  p: 3,
                  borderRadius: '50%',
                  backgroundColor: 'primary.main',
                  color: 'white',
                  mb: 3,
                  mx: 'auto',
                  width: 'fit-content',
                }}
              >
                <FlightTakeoff sx={{ fontSize: 60 }} />
              </Box>
              
              <Typography variant="h5" gutterBottom>
                No Logbook Data
              </Typography>
              <Typography variant="body1" color="text.secondary" mb={4}>
                Upload your ForeFlight CSV export to start tracking your flights, 
                aircraft, and pilot endorsements.
              </Typography>
              
              <Button
                variant="contained"
                size="large"
                startIcon={<Upload />}
                onClick={() => setUploadDialogOpen(true)}
                sx={{ px: 4, py: 1.5 }}
              >
                Upload Logbook
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        /* Dashboard Content */
        <>
          {/* Stats Cards */}
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={3}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
              >
                <Card>
                  <CardContent>
                    <Box display="flex" alignItems="center" mb={2}>
                      <Schedule color="primary" sx={{ mr: 1 }} />
                      <Typography variant="h6">Total Flight Hours</Typography>
                    </Box>
                    <Typography variant="h4" color="primary">
                      {logbookData.stats.total_hours?.toFixed(1) || '0.0'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Flight time
                    </Typography>
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
              >
                <Card>
                  <CardContent>
                    <Box display="flex" alignItems="center" mb={2}>
                      <FlightTakeoff color="primary" sx={{ mr: 1 }} />
                      <Typography variant="h6">Total Flights</Typography>
                    </Box>
                    <Typography variant="h4" color="primary">
                      {logbookData.entries?.length || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Completed flights
                    </Typography>
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
              >
                <Card>
                  <CardContent>
                    <Box display="flex" alignItems="center" mb={2}>
                      <LocationOn color="primary" sx={{ mr: 1 }} />
                      <Typography variant="h6">Aircraft</Typography>
                    </Box>
                    <Typography variant="h4" color="primary">
                      {logbookData.aircraft_stats?.length || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Different aircraft
                    </Typography>
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 }}
              >
                <Card>
                  <CardContent>
                    <Box display="flex" alignItems="center" mb={2}>
                      <TrendingUp color="primary" sx={{ mr: 1 }} />
                      <Typography variant="h6">Recent Hours</Typography>
                    </Box>
                    <Typography variant="h4" color="primary">
                      {logbookData.recent_experience?.total_hours?.toFixed(1) || '0.0'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Last 90 days
                    </Typography>
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>
          </Grid>

          {/* Student Pilot Section */}
          {user?.student_pilot && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
            >
              <Card sx={{ mb: 4 }}>
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    <School color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Student Pilot Status</Typography>
                    <Chip 
                      label="Student Pilot" 
                      color="primary" 
                      size="small" 
                      sx={{ ml: 2 }} 
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Your instructor endorsements and student-specific features are available.
                  </Typography>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Recent Flights */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
          >
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Flights
                </Typography>
                {logbookData.entries?.slice(0, 5).map((entry, index) => (
                  <Box
                    key={index}
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                    py={1}
                    borderBottom={index < 4 ? '1px solid' : 'none'}
                    borderColor="divider"
                  >
                    <Box>
                      <Typography variant="body1">
                        {entry.date} - {entry.aircraft?.registration || 'Unknown'} ({entry.aircraft?.type || 'Unknown'})
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {entry.route} • {entry.total_time}h
                      </Typography>
                    </Box>
                    <Chip 
                      label={entry.pic_time > 0 ? 'PIC' : 'Dual'} 
                      color={entry.pic_time > 0 ? 'primary' : 'secondary'}
                      size="small"
                    />
                  </Box>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        </>
      )}

      {/* Detailed Flight Data Tabs */}
      {logbookData && (
        <Box sx={{ mt: 4 }}>
          <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)}>
            <Tab label="Flight Entries" />
            <Tab label="Aircraft Statistics" />
            {user?.student_pilot && <Tab label="Endorsements" />}
          </Tabs>

          {/* Flight Entries Tab */}
          {currentTab === 0 && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Flight Entries ({filteredEntries.length} flights)
                </Typography>

                {/* Search and Filter Controls */}
                <Box sx={{ mb: 3 }}>
                  <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
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
                    <Grid item xs={12} md={3}>
                      <FormControl fullWidth>
                        <InputLabel>Sort by Date</InputLabel>
                        <Select
                          value={sortOrder}
                          onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                          label="Sort by Date"
                        >
                          <MenuItem value="desc">Latest First</MenuItem>
                          <MenuItem value="asc">Oldest First</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={5}>
                      <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                        <Typography variant="body2" sx={{ mr: 1 }}>Filter:</Typography>
                        {Object.entries(filters).map(([key, checked]) => (
                          <Chip
                            key={key}
                            label={key.toUpperCase()}
                            clickable
                            color={checked ? 'primary' : 'default'}
                            onClick={() => handleFilterChange(key as keyof typeof filters)}
                            size="small"
                          />
                        ))}
                      </Box>
                    </Grid>
                  </Grid>
                  
                  <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                    <Button
                      startIcon={showRunningTotals ? <VisibilityOff /> : <Visibility />}
                      onClick={() => setShowRunningTotals(!showRunningTotals)}
                      size="small"
                    >
                      {showRunningTotals ? 'Hide' : 'Show'} Running Totals
                    </Button>
                  </Box>
                </Box>

                {/* Flight Entries Table */}
                <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Date</TableCell>
                        <TableCell>Route</TableCell>
                        <TableCell>Aircraft</TableCell>
                        <TableCell align="right">Total</TableCell>
                        <TableCell align="right">Day/Night</TableCell>
                        <TableCell align="right">Ldg</TableCell>
                        <TableCell>Role</TableCell>
                        <TableCell align="right">PIC</TableCell>
                        <TableCell align="right">Dual</TableCell>
                        <TableCell>Status</TableCell>
                        {showRunningTotals && (
                          <>
                            <TableCell align="right">RT Total</TableCell>
                            <TableCell align="right">RT PIC</TableCell>
                            <TableCell align="right">RT XC</TableCell>
                            <TableCell align="right">RT Night</TableCell>
                          </>
                        )}
                        <TableCell width={50}></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredEntries.map((entry, index) => (
                        <React.Fragment key={index}>
                          <TableRow hover>
                            <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                            <TableCell>
                              {entry.departure?.identifier || '---'} → {entry.destination?.identifier || '---'}
                            </TableCell>
                            <TableCell>{entry.aircraft.registration}</TableCell>
                            <TableCell align="right">{entry.total_time.toFixed(1)}</TableCell>
                            <TableCell align="right">
                              {entry.conditions.day.toFixed(1)}/{entry.conditions.night.toFixed(1)}
                            </TableCell>
                            <TableCell align="right">{entry.landings_day + entry.landings_night}</TableCell>
                            <TableCell>{entry.pilot_role}</TableCell>
                            <TableCell align="right">{entry.pic_time.toFixed(1)}</TableCell>
                            <TableCell align="right">{entry.dual_received.toFixed(1)}</TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                {entry.conditions.cross_country > 0 && (
                                  <Chip label="XC" size="small" color="primary" />
                                )}
                                {entry.conditions.night > 0 && (
                                  <Chip label="Night" size="small" color="secondary" />
                                )}
                                {entry.pic_time > 0 && entry.dual_received === 0 && (
                                  <Chip label="Solo" size="small" color="success" />
                                )}
                                {entry.dual_received > 0 && (
                                  <Chip label="Dual" size="small" color="warning" />
                                )}
                              </Box>
                            </TableCell>
                            {showRunningTotals && (
                              <>
                                <TableCell align="right">{entry.running_totals.total_time.toFixed(1)}</TableCell>
                                <TableCell align="right">{entry.running_totals.pic_time.toFixed(1)}</TableCell>
                                <TableCell align="right">{entry.running_totals.cross_country.toFixed(1)}</TableCell>
                                <TableCell align="right">{entry.running_totals.night_time.toFixed(1)}</TableCell>
                              </>
                            )}
                            <TableCell>
                              <IconButton
                                size="small"
                                onClick={() => toggleRowExpansion(index)}
                              >
                                {expandedRows.has(index) ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
                              </IconButton>
                            </TableCell>
                          </TableRow>
                          
                          {/* Expanded Row Details */}
                          <TableRow>
                            <TableCell colSpan={showRunningTotals ? 15 : 11} sx={{ p: 0 }}>
                              <Collapse in={expandedRows.has(index)} timeout="auto" unmountOnExit>
                                <Box sx={{ p: 2, bgcolor: 'grey.50' }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    Flight Details
                                  </Typography>
                                  <Grid container spacing={2}>
                                    <Grid item xs={12} sm={6} md={3}>
                                      <Typography variant="body2" color="text.secondary">
                                        Aircraft Details
                                      </Typography>
                                      <Typography variant="body2">
                                        Registration: {entry.aircraft.registration}<br />
                                        Type: {entry.aircraft.type}<br />
                                        Category/Class: {entry.aircraft.category_class}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6} md={3}>
                                      <Typography variant="body2" color="text.secondary">
                                        Flight Times
                                      </Typography>
                                      <Typography variant="body2">
                                        Total: {entry.total_time.toFixed(1)}<br />
                                        Day: {entry.conditions.day.toFixed(1)}<br />
                                        Night: {entry.conditions.night.toFixed(1)}<br />
                                        Cross Country: {entry.conditions.cross_country.toFixed(1)}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6} md={3}>
                                      <Typography variant="body2" color="text.secondary">
                                        Landings & Conditions
                                      </Typography>
                                      <Typography variant="body2">
                                        Day Landings: {entry.landings_day}<br />
                                        Night Landings: {entry.landings_night}<br />
                                        Sim Instrument: {entry.conditions.simulated_instrument.toFixed(1)}<br />
                                        Actual Instrument: {entry.conditions.actual_instrument.toFixed(1)}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6} md={3}>
                                      <Typography variant="body2" color="text.secondary">
                                        Running Totals
                                      </Typography>
                                      <Typography variant="body2">
                                        Total Time: {entry.running_totals.total_time.toFixed(1)}<br />
                                        PIC Time: {entry.running_totals.pic_time.toFixed(1)}<br />
                                        Dual Received: {entry.running_totals.dual_received.toFixed(1)}<br />
                                        Cross Country: {entry.running_totals.cross_country.toFixed(1)}
                                      </Typography>
                                    </Grid>
                                    {entry.remarks && (
                                      <Grid item xs={12}>
                                        <Typography variant="body2" color="text.secondary">
                                          Remarks
                                        </Typography>
                                        <Typography variant="body2">{entry.remarks}</Typography>
                                      </Grid>
                                    )}
                                  </Grid>
                                </Box>
                              </Collapse>
                            </TableCell>
                          </TableRow>
                        </React.Fragment>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          {/* Aircraft Statistics Tab */}
          {currentTab === 1 && logbookData.aircraft_stats && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Aircraft Statistics ({logbookData.aircraft_stats.length} aircraft)
                </Typography>
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Registration</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell align="right">Flights</TableCell>
                        <TableCell align="right">Total Time</TableCell>
                        <TableCell align="right">Avg per Flight</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {logbookData.aircraft_stats.map((aircraft, index) => (
                        <TableRow key={index}>
                          <TableCell>{aircraft.registration}</TableCell>
                          <TableCell>{aircraft.type}</TableCell>
                          <TableCell align="right">{aircraft.flights}</TableCell>
                          <TableCell align="right">{aircraft.total_time.toFixed(1)}</TableCell>
                          <TableCell align="right">
                            {aircraft.flights > 0 ? (aircraft.total_time / aircraft.flights).toFixed(1) : '0.0'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          {/* Endorsements Tab (Student Pilot Only) */}
          {currentTab === 2 && user?.student_pilot && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Instructor Endorsements
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  This feature will be implemented to manage instructor endorsements for student pilots.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Box>
      )}

      {/* Upload FAB */}
      <Fab
        color="primary"
        aria-label="upload"
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
        }}
        onClick={() => setUploadDialogOpen(true)}
      >
        <Add />
      </Fab>

      {/* Upload Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload Logbook</DialogTitle>
        <DialogContent>
          <Box mb={2}>
            <TextField
              type="file"
              inputProps={{ accept: '.csv' }}
              onChange={handleFileChange}
              fullWidth
              variant="outlined"
            />
          </Box>
          <FormControlLabel
            control={
              <Checkbox
                checked={isStudentPilot}
                onChange={(e) => setIsStudentPilot(e.target.checked)}
              />
            }
            label="I am a student pilot"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleFileUpload}
            variant="contained"
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DashboardPage

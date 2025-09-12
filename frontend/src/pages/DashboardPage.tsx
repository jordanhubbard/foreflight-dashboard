import React, { useState, useEffect } from 'react'
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
} from '@mui/material'
import {
  FlightTakeoff,
  Upload,
  School,
  TrendingUp,
  Schedule,
  LocationOn,
  Add,
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

  useEffect(() => {
    loadLogbookData()
  }, [])

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

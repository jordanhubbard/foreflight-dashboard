import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Avatar,
  Chip,
} from '@mui/material'
import {
  Person,
  Email,
  Badge,
  School,
  Edit,
  Save,
  Cancel,
} from '@mui/icons-material'
import { motion } from 'framer-motion'
import { useAuthStore } from '../hooks/useAuthStore'
import toast from 'react-hot-toast'

const ProfilePage: React.FC = () => {
  const { user, updateProfile } = useAuthStore()
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    pilot_certificate_number: user?.pilot_certificate_number || '',
    student_pilot: user?.student_pilot || false,
  })

  const handleSave = async () => {
    try {
      await updateProfile(formData)
      setIsEditing(false)
      toast.success('Profile updated successfully!')
    } catch (error) {
      toast.error('Failed to update profile')
    }
  }

  const handleCancel = () => {
    setFormData({
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      pilot_certificate_number: user?.pilot_certificate_number || '',
      student_pilot: user?.student_pilot || false,
    })
    setIsEditing(false)
  }

  return (
    <Box>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography variant="h4" component="h1" gutterBottom>
          Profile
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={4}>
          Manage your account information and preferences.
        </Typography>
      </motion.div>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 4 }}>
                <Avatar
                  sx={{
                    width: 100,
                    height: 100,
                    mx: 'auto',
                    mb: 2,
                    bgcolor: 'primary.main',
                    fontSize: '2.5rem',
                  }}
                >
                  {user?.first_name?.[0]?.toUpperCase()}
                </Avatar>
                <Typography variant="h5" gutterBottom>
                  {user?.full_name}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  {user?.email}
                </Typography>
                {user?.student_pilot && (
                  <Chip
                    label="Student Pilot"
                    color="primary"
                    icon={<School />}
                    sx={{ mb: 2 }}
                  />
                )}
                <Typography variant="body2" color="text.secondary">
                  Member since {new Date(user?.created_at || '').toLocaleDateString()}
                </Typography>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        <Grid item xs={12} md={8}>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                  <Typography variant="h6">Personal Information</Typography>
                  {!isEditing ? (
                    <Button
                      startIcon={<Edit />}
                      onClick={() => setIsEditing(true)}
                      variant="outlined"
                    >
                      Edit
                    </Button>
                  ) : (
                    <Box>
                      <Button
                        startIcon={<Save />}
                        onClick={handleSave}
                        variant="contained"
                        sx={{ mr: 1 }}
                      >
                        Save
                      </Button>
                      <Button
                        startIcon={<Cancel />}
                        onClick={handleCancel}
                        variant="outlined"
                      >
                        Cancel
                      </Button>
                    </Box>
                  )}
                </Box>

                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="First Name"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                      disabled={!isEditing}
                      fullWidth
                      InputProps={{
                        startAdornment: <Person sx={{ mr: 1, color: 'action.active' }} />,
                      }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Last Name"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                      disabled={!isEditing}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      label="Email"
                      value={user?.email}
                      disabled
                      fullWidth
                      InputProps={{
                        startAdornment: <Email sx={{ mr: 1, color: 'action.active' }} />,
                      }}
                      helperText="Email cannot be changed"
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      label="Pilot Certificate Number"
                      value={formData.pilot_certificate_number}
                      onChange={(e) => setFormData({ ...formData, pilot_certificate_number: e.target.value })}
                      disabled={!isEditing}
                      fullWidth
                      InputProps={{
                        startAdornment: <Badge sx={{ mr: 1, color: 'action.active' }} />,
                      }}
                      helperText="Optional: Your pilot certificate number"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>
    </Box>
  )
}

export default ProfilePage

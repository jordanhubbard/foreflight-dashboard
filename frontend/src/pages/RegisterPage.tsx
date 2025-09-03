import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  FormControlLabel,
  Checkbox,
  Link,
  Grid,
} from '@mui/material'
import {
  FlightTakeoff,
  Email,
  Lock,
  Person,
  Badge,
} from '@mui/icons-material'
import { useForm } from 'react-hook-form'
import { yupResolver } from '@hookform/resolvers/yup'
import * as yup from 'yup'
import { motion } from 'framer-motion'
import { useNavigate, Link as RouterLink } from 'react-router-dom'
import { useAuthStore, RegisterData } from '../hooks/useAuthStore'
import toast from 'react-hot-toast'

const schema = yup.object({
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'Password must contain at least one uppercase letter, one lowercase letter, and one number'
    )
    .required('Password is required'),
  password_confirm: yup
    .string()
    .oneOf([yup.ref('password')], 'Passwords must match')
    .required('Please confirm your password'),
  first_name: yup
    .string()
    .min(1, 'First name is required')
    .max(50, 'First name must be less than 50 characters')
    .required('First name is required'),
  last_name: yup
    .string()
    .min(1, 'Last name is required')
    .max(50, 'Last name must be less than 50 characters')
    .required('Last name is required'),
  pilot_certificate_number: yup
    .string()
    .max(20, 'Certificate number must be less than 20 characters'),
  student_pilot: yup.boolean(),

})

type RegisterFormData = yup.InferType<typeof schema>

const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const { register: registerUser, error, clearError, isAuthenticated } = useAuthStore()
  const [isStudentPilot, setIsStudentPilot] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: yupResolver(schema),
    defaultValues: {
      student_pilot: false,
    },
  })

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard')
    }
  }, [isAuthenticated, navigate])

  useEffect(() => {
    if (error) {
      toast.error(error)
      clearError()
    }
  }, [error, clearError])

  const onSubmit = async (data: RegisterFormData) => {
    try {
      const registerData: RegisterData = {
        ...data,
        student_pilot: isStudentPilot,
      }
      await registerUser(registerData)
      toast.success('Account created successfully! Please check your email to verify your account.')
      navigate('/login')
    } catch (error) {
      // Error is handled by the store and useEffect
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: 2,
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Card
          sx={{
            maxWidth: 600,
            width: '100%',
            borderRadius: 3,
            boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
          }}
        >
          <CardContent sx={{ p: 4 }}>
            <Box
              display="flex"
              flexDirection="column"
              alignItems="center"
              mb={4}
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
              >
                <Box
                  sx={{
                    p: 2,
                    borderRadius: '50%',
                    backgroundColor: 'primary.main',
                    color: 'white',
                    mb: 2,
                  }}
                >
                  <FlightTakeoff sx={{ fontSize: 40 }} />
                </Box>
              </motion.div>
              
              <Typography variant="h4" component="h1" gutterBottom>
                Create Account
              </Typography>
              <Typography variant="body2" color="text.secondary" textAlign="center">
                Join the ForeFlight Dashboard community - Free, open-source aviation tool
              </Typography>
            </Box>

            <Box component="form" onSubmit={handleSubmit(onSubmit)}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    {...register('first_name')}
                    fullWidth
                    label="First Name"
                    error={!!errors.first_name}
                    helperText={errors.first_name?.message}
                    InputProps={{
                      startAdornment: (
                        <Person color="action" sx={{ mr: 1 }} />
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    {...register('last_name')}
                    fullWidth
                    label="Last Name"
                    error={!!errors.last_name}
                    helperText={errors.last_name?.message}
                    InputProps={{
                      startAdornment: (
                        <Person color="action" sx={{ mr: 1 }} />
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    {...register('email')}
                    fullWidth
                    label="Email Address"
                    type="email"
                    error={!!errors.email}
                    helperText={errors.email?.message}
                    InputProps={{
                      startAdornment: (
                        <Email color="action" sx={{ mr: 1 }} />
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    {...register('pilot_certificate_number')}
                    fullWidth
                    label="Pilot Certificate Number (Optional)"
                    error={!!errors.pilot_certificate_number}
                    helperText={errors.pilot_certificate_number?.message}
                    InputProps={{
                      startAdornment: (
                        <Badge color="action" sx={{ mr: 1 }} />
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    {...register('password')}
                    fullWidth
                    label="Password"
                    type="password"
                    error={!!errors.password}
                    helperText={errors.password?.message}
                    InputProps={{
                      startAdornment: (
                        <Lock color="action" sx={{ mr: 1 }} />
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    {...register('password_confirm')}
                    fullWidth
                    label="Confirm Password"
                    type="password"
                    error={!!errors.password_confirm}
                    helperText={errors.password_confirm?.message}
                    InputProps={{
                      startAdornment: (
                        <Lock color="action" sx={{ mr: 1 }} />
                      ),
                    }}
                  />
                </Grid>
              </Grid>

              <Box my={3}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={isStudentPilot}
                      onChange={(e) => setIsStudentPilot(e.target.checked)}
                      color="primary"
                    />
                  }
                  label="I am a student pilot"
                />
              </Box>

              <Box mb={3}>
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  This is a free, open-source aviation tool. No terms to agree to.
                </Typography>
              </Box>

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={isSubmitting}
                sx={{
                  py: 1.5,
                  mb: 2,
                  borderRadius: 2,
                  textTransform: 'none',
                  fontSize: '1.1rem',
                }}
              >
                {isSubmitting ? 'Creating Account...' : 'Create Account'}
              </Button>

              <Box textAlign="center">
                <Typography variant="body2" color="text.secondary">
                  Already have an account?{' '}
                  <Link
                    component={RouterLink}
                    to="/login"
                    color="primary"
                    sx={{ textDecoration: 'none', fontWeight: 500 }}
                  >
                    Sign in
                  </Link>
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  )
}

export default RegisterPage

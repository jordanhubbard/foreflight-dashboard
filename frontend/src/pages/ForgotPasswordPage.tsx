import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Link,
} from '@mui/material'
import {
  FlightTakeoff,
  Email,
  ArrowBack,
} from '@mui/icons-material'
import { useForm } from 'react-hook-form'
import { yupResolver } from '@hookform/resolvers/yup'
import * as yup from 'yup'
import { motion } from 'framer-motion'
import { useNavigate, Link as RouterLink } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuthStore'
import toast from 'react-hot-toast'

const schema = yup.object({
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required'),
})

type ForgotPasswordFormData = yup.InferType<typeof schema>

const ForgotPasswordPage: React.FC = () => {
  const navigate = useNavigate()
  const { forgotPassword, error, clearError, isAuthenticated } = useAuthStore()
  const [isSubmitted, setIsSubmitted] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: yupResolver(schema),
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

  const onSubmit = async (data: ForgotPasswordFormData) => {
    try {
      await forgotPassword(data.email)
      setIsSubmitted(true)
      toast.success('Password reset email sent!')
    } catch (error) {
      // Error is handled by the store and useEffect
    }
  }

  if (isSubmitted) {
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
              maxWidth: 400,
              width: '100%',
              borderRadius: 3,
              boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
            }}
          >
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: '50%',
                  backgroundColor: 'success.main',
                  color: 'white',
                  mb: 2,
                  mx: 'auto',
                  width: 'fit-content',
                }}
              >
                <Email sx={{ fontSize: 40 }} />
              </Box>
              
              <Typography variant="h4" component="h1" gutterBottom>
                Check Your Email
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                We've sent a password reset link to your email address. 
                Please check your inbox and follow the instructions to reset your password.
              </Typography>
              
              <Button
                component={RouterLink}
                to="/login"
                variant="outlined"
                startIcon={<ArrowBack />}
                fullWidth
                sx={{ mb: 2 }}
              >
                Back to Sign In
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </Box>
    )
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
            maxWidth: 400,
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
                Reset Password
              </Typography>
              <Typography variant="body2" color="text.secondary" textAlign="center">
                Enter your email address and we'll send you a link to reset your password.
              </Typography>
            </Box>

            <Box component="form" onSubmit={handleSubmit(onSubmit)}>
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
                sx={{ mb: 3 }}
              />

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
                {isSubmitting ? 'Sending...' : 'Send Reset Link'}
              </Button>

              <Box textAlign="center">
                <Typography variant="body2" color="text.secondary">
                  Remember your password?{' '}
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

export default ForgotPasswordPage

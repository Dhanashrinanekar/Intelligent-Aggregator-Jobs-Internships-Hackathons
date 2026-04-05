
"""User Registration and Authentication Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserResponse, SendOTPRequest, VerifyOTPRequest, OTPResponse, PasswordResetRequest, PasswordResetConfirm
from app.auth.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.config import settings
from app.services.otp_service import OTPService

router = APIRouter()

@router.post("/send-otp", response_model=OTPResponse)
async def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    """Send OTP to user email for verification"""
    email = request.email
    
    # Check if email already exists and is verified
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user and existing_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered and verified"
        )
    
    try:
        # Generate and create OTP
        otp = OTPService.create_otp(db, email)
        
        # Send OTP to email
        success = OTPService.send_otp_email(email, otp)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email"
            )
        
        return OTPResponse(
            message="OTP sent successfully to your email",
            email=email
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending OTP: {str(e)}"
        )

@router.post("/verify-otp", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify OTP and complete user registration"""
    email = request.email
    otp = request.otp
    
    try:
        # Verify OTP
        is_valid = OTPService.verify_otp(db, email, otp)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            # Update existing user
            if request.password:
                existing_user.password = get_password_hash(request.password)
            existing_user.is_verified = True
            db.commit()
            db.refresh(existing_user)
            return existing_user
        else:
            # Create new user
            if not request.name or not request.password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Name and password required for new user registration"
                )
            
            hashed_password = get_password_hash(request.password)
            new_user = User(
                name=request.name,
                email=email,
                password=hashed_password,
                is_verified=True
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            return new_user
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying OTP: {str(e)}"
        )

@router.post("/password-reset/request", response_model=OTPResponse)
async def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Send password reset OTP by email"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist"
        )

    otp = OTPService.create_otp(db, user.email, user.user_id)
    sent = OTPService.send_password_reset_email(user.email, otp)

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )

    return OTPResponse(
        message="Password reset link has been sent to your email.",
        email=user.email
    )

@router.post("/password-reset/confirm")
async def confirm_password_reset(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Verify OTP and reset password"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found"
        )

    is_valid = OTPService.verify_otp(db, request.email, request.otp)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    user.password = get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password has been reset successfully"}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user (deprecated - use send-otp and verify-otp instead)"""
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        is_verified=True
    )
   

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token)
async def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@router.put("/me/skills")
async def update_skills(
    skills: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user skills"""
    current_user.skills = skills
    db.commit()
    return {"message": "Skills updated successfully"}
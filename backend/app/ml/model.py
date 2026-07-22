"""
ML Training Module

Handles LightGBM model training, evaluation, and artifact management.
"""
from typing import Dict, Tuple, Optional, Any
from datetime import datetime
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, roc_curve
import lightgbm as lgb

from app.config import settings
from app.ml.features import FeatureCalculator, get_reference_time_from_data


class LightGBMTrainer:
    """
    LightGBM Model Trainer

    Orchestrates the complete training pipeline:
    - Data loading and preparation
    - Feature engineering for ML
    - Train/test split
    - Model training
    - Evaluation (AUC, KS, feature importance)
    - Model artifact saving
    """

    # Official 13 risk features for model training
    # Single source of truth for feature count
    OFFICIAL_FEATURES = [
        'trade_frequency_7d',
        'trade_frequency_24h',
        'trade_volume_24h',
        'withdrawal_volume_24h',
        'account_age_days',
        'avg_trade_size',
        'shared_device_count',
        'linked_account_count',
        'unique_ip_count',
        'withdrawal_frequency_24h',
        'withdrawal_risk_score',
        'opposite_trade_ratio',
        'active_days_count',
    ]

    def __init__(self, model_path: Optional[str] = None):
        """Initialize trainer with model path."""
        self.model_path = model_path or settings.MODEL_PATH
        Path(self.model_path).mkdir(parents=True, exist_ok=True)

        self.model = None
        self.feature_names = None
        self.evaluation_results = {}

    def prepare_features(
        self,
        users_df: pd.DataFrame,
        devices_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        withdrawals_df: pd.DataFrame,
        labels_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Prepare feature table for ML training using shared FeatureCalculator.

        This ensures training-serving feature consistency.
        """
        # Calculate reference time from training data
        reference_time = get_reference_time_from_data(trades_df, withdrawals_df)

        # Initialize shared FeatureCalculator
        calculator = FeatureCalculator(reference_time)

        features_list = []

        for user_id in labels_df['user_id'].unique():
            user_features = self._calculate_user_features(
                user_id,
                users_df,
                devices_df,
                trades_df,
                withdrawals_df,
                calculator
            )
            features_list.append(user_features)

        features_df = pd.DataFrame(features_list)

        # Merge with labels
        features_df = features_df.merge(labels_df, on='user_id', how='left')

        return features_df

    def _calculate_user_features(
        self,
        user_id: str,
        users_df: pd.DataFrame,
        devices_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        withdrawals_df: pd.DataFrame,
        calculator: FeatureCalculator
    ) -> Dict[str, Any]:
        """Calculate all features for a single user using shared FeatureCalculator."""
        user = users_df[users_df['user_id'] == user_id].iloc[0] if len(users_df[users_df['user_id'] == user_id]) > 0 else None
        user_devices = devices_df[devices_df['user_id'] == user_id]
        user_trades = trades_df[trades_df['user_id'] == user_id]
        user_withdrawals = withdrawals_df[withdrawals_df['user_id'] == user_id]

        features = {'user_id': user_id}

        # Trading features
        trading_features = calculator.calculate_trading_features(user_trades)
        features.update(trading_features)

        # Withdrawal features
        withdrawal_features = calculator.calculate_withdrawal_features(user_withdrawals)
        features.update(withdrawal_features)

        # Temporal features
        temporal_features = calculator.calculate_temporal_features(user, user_trades, user_withdrawals)
        features.update(temporal_features)

        # Device features (need all_devices for shared device calculation)
        device_features = calculator.calculate_device_features(user_devices, devices_df)
        features.update(device_features)

        return features

    def train(
        self,
        features_df: pd.DataFrame,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        Train LightGBM model on prepared features.

        Args:
            features_df: DataFrame with features and 'is_risky' label
            test_size: Proportion of data for testing
            random_state: Random seed for reproducibility

        Returns:
            Training results with metrics
        """
        # Separate features and target
        # Use only the official 13 risk features (single source of truth)
        feature_cols = [c for c in self.OFFICIAL_FEATURES if c in features_df.columns]

        if len(feature_cols) != 13:
            raise ValueError(f"Expected 13 official features, found {len(feature_cols)}: {feature_cols}")

        X = features_df[feature_cols].copy()
        y = features_df['is_risky'].copy()

        # Handle missing values
        X = X.fillna(0)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        # Create LightGBM dataset
        train_data = lgb.Dataset(X_train, label=y_train)
        test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        # Training parameters
        params = {
            'objective': 'binary',
            'metric': ['auc', 'binary_logloss'],
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': random_state,
        }

        # Train model
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=100,
            valid_sets=[train_data, test_data],
        )

        self.feature_names = feature_cols

        # Evaluate
        self.evaluation_results = self._evaluate_model(X_test, y_test)

        # Save model
        self._save_model()

        return {
            'feature_importance': self.evaluation_results['feature_importance'],
            'metrics': {
                'auc': self.evaluation_results['auc'],
                'ks': self.evaluation_results['ks'],
            },
            'train_size': len(X_train),
            'test_size': len(X_test),
            'positive_ratio': y.mean(),
        }

    def _evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """Evaluate model and calculate metrics."""
        # Get predictions
        y_pred_proba = self.model.predict(X_test)
        y_pred = (y_pred_proba >= 0.5).astype(int)

        # AUC
        auc_score = roc_auc_score(y_test, y_pred_proba)

        # KS statistic
        fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
        ks_score = max(tpr - fpr)

        # Feature importance
        feature_importance = self.model.feature_importance(importance_type='gain')

        importance_dict = dict(zip(self.feature_names, feature_importance))
        sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

        return {
            'auc': auc_score,
            'ks': ks_score,
            'feature_importance': [
                {'feature': f, 'importance': float(i)}
                for f, i in sorted_importance
            ],
        }

    def _save_model(self):
        """Save model artifact."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_filename = f'risk_model_{timestamp}.pkl'
        model_path = Path(self.model_path) / model_filename

        artifact = {
            'model': self.model,
            'feature_names': self.feature_names,
            'metadata': {
                'trained_at': datetime.now().isoformat(),
                'version': timestamp,
            },
            'evaluation': self.evaluation_results,
        }

        joblib.dump(artifact, model_path)

        # Also save as latest for easy loading
        latest_path = Path(self.model_path) / 'risk_model_latest.pkl'
        joblib.dump(artifact, latest_path)

        return str(model_path)

    def save_baseline_distribution(
        self,
        features_df: pd.DataFrame,
        output_path: Optional[str] = None
    ) -> str:
        """
        Save feature distribution baseline for PSI monitoring.

        Args:
            features_df: DataFrame with features
            output_path: Where to save baseline JSON

        Returns:
            Path to saved baseline file
        """
        from app.ml.psi import PSIAnalyzer

        if output_path is None:
            output_path = str(Path(self.model_path) / "feature_baseline.json")

        analyzer = PSIAnalyzer(n_bins=10)

        # Use only the official 13 risk features for baseline
        feature_cols = [c for c in self.OFFICIAL_FEATURES if c in features_df.columns]

        baseline = analyzer.create_baseline_distribution(features_df, feature_cols)
        analyzer.save_baseline(baseline, output_path)

        return output_path


class MLInferenceService:
    """
    ML Inference Service

    Loads trained model and performs inference.
    Separated from training to allow independent deployment.
    """

    def __init__(self, model_path: Optional[str] = None):
        """Initialize inference service."""
        self.model_path = model_path or f"{settings.MODEL_PATH}/risk_model_latest.pkl"
        self.artifact = None
        self.model = None
        self.feature_names = None
        self._load_model()

    def _load_model(self):
        """Load trained model artifact."""
        try:
            print(f"[Model Verification] Loading model from: {self.model_path}")
            self.artifact = joblib.load(self.model_path)
            self.model = self.artifact['model']
            self.feature_names = self.artifact['feature_names']
            print(f"[Model Verification] ✓ Model loaded successfully")
            print(f"[Model Verification]   Model type: {type(self.model).__name__}")
            print(f"[Model Verification]   Feature count: {len(self.feature_names)}")
            print(f"[Model Verification]   Features: {self.feature_names}")
        except Exception as e:
            print(f"[Model Verification] ✗ Could not load model from {self.model_path}: {e}")
            print("[Model Verification] Using fallback heuristic scoring")
            self.model = None

    def predict_proba(self, features: Dict[str, float]) -> Tuple[float, float]:
        """
        Predict probability for a single user.

        Returns:
            (risk_probability, risk_score_0_100)
        """
        if self.model is None:
            # Fallback to heuristic
            print("[Model Verification] Using fallback heuristic prediction")
            return self._fallback_prediction(features)

        # Prepare feature vector
        feature_vector = self._prepare_feature_vector(features)
        print(f"[Model Verification] Feature vector shape: {feature_vector.shape}")

        # Get prediction
        probability = self.model.predict(feature_vector)[0]
        print(f"[Model Verification] Prediction probability: {probability}")

        # Convert to 0-100 score
        score = probability * 100

        return float(probability), float(score)

    def _prepare_feature_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Prepare feature vector in correct order."""
        feature_values = []
        for fname in self.feature_names:
            value = features.get(fname, 0)
            if pd.isna(value):
                value = 0
            feature_values.append(value)

        return np.array([feature_values])

    def _fallback_prediction(self, features: Dict[str, float]) -> Tuple[float, float]:
        """Fallback heuristic prediction when model not available."""
        score = 50.0  # Base score

        # Simple heuristic
        if features.get('shared_device_count', 0) > 0:
            score += min(features['shared_device_count'] * 8, 30)

        if features.get('opposite_trade_ratio', 0) > 0:
            score += features['opposite_trade_ratio'] * 30

        probability = score / 100
        return probability, score

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded model."""
        if self.artifact is None:
            return {
                'model_loaded': False,
                'message': 'No model available',
            }

        return {
            'model_loaded': True,
            'trained_at': self.artifact['metadata'].get('trained_at'),
            'version': self.artifact['metadata'].get('version'),
            'evaluation': self.artifact.get('evaluation', {}),
            'feature_count': len(self.feature_names),
        }

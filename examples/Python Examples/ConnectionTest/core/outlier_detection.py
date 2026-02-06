"""
Outlier Detection Module for Skewed Error Metrics

This module provides robust outlier detection methods optimized for 
right-skewed, positive-only data like error metrics (MAE, RMSE, etc.).

Key characteristics of error metrics:
- Always >= 0 (bounded at zero)
- Typically right-skewed (long tail on high values)
- Often leptokurtic (heavy tails)

Recommended Usage:
    from outlier_detection import OutlierDetector
    
    detector = OutlierDetector(df, value_col='Error_MAE', group_col='Condition')
    results = detector.detect_all()
    
    # Get consensus outliers
    df['is_outlier'] = detector.consensus(min_methods=3)

Author: SystemLink Examples
Date: February 2026
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Union, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OutlierResult:
    """Container for outlier detection results."""
    method: str
    outlier_mask: pd.Series
    count: int
    percentage: float
    bounds: Optional[Dict] = None
    notes: str = ""


class OutlierDetector:
    """
    Robust outlier detection for skewed error metrics.
    
    Implements multiple detection methods optimized for positive, 
    right-skewed data typical of error metrics.
    
    Attributes:
        df: DataFrame containing the data
        value_col: Column name containing values to analyze
        group_col: Optional column for group-wise detection
        
    Example:
        >>> detector = OutlierDetector(df, 'Error_MAE', 'Condition')
        >>> results = detector.detect_all()
        >>> print(results['log_sigma'].percentage)
        3.52
        >>> 
        >>> # Get high-confidence outliers
        >>> df['outlier'] = detector.consensus(min_methods=3)
    """
    
    def __init__(self, df: pd.DataFrame, value_col: str, 
                 group_col: Optional[str] = None):
        """
        Initialize the outlier detector.
        
        Args:
            df: DataFrame with the data
            value_col: Column containing numeric values to analyze
            group_col: Optional column for group-wise analysis
        """
        self.df = df.copy()
        self.value_col = value_col
        self.group_col = group_col
        self.results: Dict[str, OutlierResult] = {}
        
        # Ensure numeric
        self.df[value_col] = pd.to_numeric(self.df[value_col], errors='coerce')
        
        # Compute basic stats
        self.stats = {
            'mean': self.df[value_col].mean(),
            'std': self.df[value_col].std(),
            'median': self.df[value_col].median(),
            'skewness': self.df[value_col].skew(),
            'kurtosis': self.df[value_col].kurtosis(),
            'min': self.df[value_col].min(),
            'max': self.df[value_col].max(),
            'n': len(self.df)
        }
        
        logger.info(f"Initialized OutlierDetector: {value_col}, "
                   f"n={self.stats['n']}, skew={self.stats['skewness']:.2f}")

    def _apply_grouped(self, func: Callable, **kwargs) -> pd.Series:
        """Apply function globally or per group."""
        if self.group_col:
            return self.df.groupby(self.group_col)[self.value_col].transform(func, **kwargs)
        else:
            return func(self.df[self.value_col], **kwargs)

    # ========================================================================
    # METHOD 1: LOG-TRANSFORM + SIGMA (Best for skewed positive data)
    # ========================================================================
    
    def log_sigma(self, k: float = 3.0) -> OutlierResult:
        """
        Log-transform + k-sigma rule.
        
        RECOMMENDED for right-skewed positive data like error metrics.
        Transforms data to log-space where it's more symmetric, then 
        applies standard sigma rule.
        
        Args:
            k: Number of standard deviations for threshold (default: 3)
            
        Returns:
            OutlierResult with outlier mask and stats
            
        Example:
            >>> result = detector.log_sigma(k=3)
            >>> print(f"Found {result.count} outliers ({result.percentage:.2f}%)")
        """
        def _log_sigma_func(group, k=3):
            log_vals = np.log(group.replace(0, np.nan))  # Avoid log(0)
            mean = log_vals.mean()
            std = log_vals.std()
            return (log_vals < mean - k * std) | (log_vals > mean + k * std)
        
        mask = self._apply_grouped(_log_sigma_func, k=k)
        mask = mask.fillna(False).astype(bool)
        
        # Calculate bounds in original space
        log_vals = np.log(self.df[self.value_col].replace(0, np.nan))
        log_mean, log_std = log_vals.mean(), log_vals.std()
        lower_log = log_mean - k * log_std
        upper_log = log_mean + k * log_std
        
        result = OutlierResult(
            method='log_sigma',
            outlier_mask=mask,
            count=int(mask.sum()),
            percentage=mask.mean() * 100,
            bounds={
                'lower': np.exp(lower_log),
                'upper': np.exp(upper_log),
                'lower_log': lower_log,
                'upper_log': upper_log
            },
            notes=f"Log-transform + {k}σ rule. Reduces skewness from "
                  f"{self.stats['skewness']:.2f} to {log_vals.skew():.2f}"
        )
        self.results['log_sigma'] = result
        return result

    # ========================================================================
    # METHOD 2: ASYMMETRIC MAD (Robust, handles skewness)
    # ========================================================================
    
    def asymmetric_mad(self, threshold: float = 3.5) -> OutlierResult:
        """
        Asymmetric Median Absolute Deviation.
        
        Uses separate MAD values for left and right tails, making it 
        robust to skewness. Based on median, resistant to outliers.
        
        Args:
            threshold: Modified Z-score threshold (default: 3.5)
            
        Returns:
            OutlierResult with outlier mask and stats
            
        Note:
            The 0.6745 constant scales MAD to be comparable to standard 
            deviation for normally distributed data.
        """
        def _asym_mad_func(group, threshold=3.5):
            median = group.median()
            
            below = group[group <= median]
            above = group[group >= median]
            
            # Separate MAD for each tail
            mad_lower = (median - below).median() if len(below) > 0 else group.std() * 0.6745
            mad_upper = (above - median).median() if len(above) > 0 else group.std() * 0.6745
            
            # Handle zero MAD
            if mad_lower == 0:
                mad_lower = group.std() * 0.6745
            if mad_upper == 0:
                mad_upper = group.std() * 0.6745
            
            # Modified Z-scores for each tail
            z_lower = np.where(group < median, 0.6745 * (median - group) / mad_lower, 0)
            z_upper = np.where(group > median, 0.6745 * (group - median) / mad_upper, 0)
            
            return pd.Series((z_lower > threshold) | (z_upper > threshold), index=group.index)
        
        mask = self._apply_grouped(_asym_mad_func, threshold=threshold)
        mask = mask.fillna(False).astype(bool)
        
        result = OutlierResult(
            method='asymmetric_mad',
            outlier_mask=mask,
            count=int(mask.sum()),
            percentage=mask.mean() * 100,
            notes=f"Asymmetric MAD with threshold={threshold}. "
                  f"Robust to outliers and skewness."
        )
        self.results['asymmetric_mad'] = result
        return result

    # ========================================================================
    # METHOD 3: ASYMMETRIC SIGMA (Separate σ_lower / σ_upper)
    # ========================================================================
    
    def asymmetric_sigma(self, k_lower: float = 3.0, k_upper: float = 3.0) -> OutlierResult:
        """
        Asymmetric sigma with separate multipliers for each tail.
        
        Computes standard deviation separately for values below and above
        the median, then applies different k-values for each bound.
        
        Args:
            k_lower: Sigma multiplier for lower bound (default: 3)
            k_upper: Sigma multiplier for upper bound (default: 3)
            
        Returns:
            OutlierResult with outlier mask and stats
            
        Note:
            For error metrics where only high values are concerning,
            set k_lower=float('inf') to only flag upper outliers.
        """
        def _asym_sigma_func(group, k_lower=3, k_upper=3):
            median = group.median()
            below = group[group <= median]
            above = group[group >= median]
            
            std_lower = below.std() if len(below) > 1 else group.std()
            std_upper = above.std() if len(above) > 1 else group.std()
            
            lower_bound = median - k_lower * std_lower
            upper_bound = median + k_upper * std_upper
            
            return pd.Series((group < lower_bound) | (group > upper_bound), index=group.index)
        
        mask = self._apply_grouped(_asym_sigma_func, k_lower=k_lower, k_upper=k_upper)
        mask = mask.fillna(False).astype(bool)
        
        result = OutlierResult(
            method='asymmetric_sigma',
            outlier_mask=mask,
            count=int(mask.sum()),
            percentage=mask.mean() * 100,
            notes=f"Asymmetric σ with k_lower={k_lower}, k_upper={k_upper}"
        )
        self.results['asymmetric_sigma'] = result
        return result

    # ========================================================================
    # METHOD 4: IQR (Non-parametric, no distribution assumption)
    # ========================================================================
    
    def iqr(self, k: float = 1.5) -> OutlierResult:
        """
        Interquartile Range method.
        
        Non-parametric method using Q1, Q3 quartiles. Makes no assumption
        about the underlying distribution.
        
        Args:
            k: IQR multiplier (1.5 = mild outliers, 3.0 = extreme only)
            
        Returns:
            OutlierResult with outlier mask and stats
        """
        def _iqr_func(group, k=1.5):
            q1, q3 = group.quantile(0.25), group.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - k * iqr
            upper = q3 + k * iqr
            return pd.Series((group < lower) | (group > upper), index=group.index)
        
        mask = self._apply_grouped(_iqr_func, k=k)
        mask = mask.fillna(False).astype(bool)
        
        q1, q3 = self.df[self.value_col].quantile([0.25, 0.75])
        iqr_val = q3 - q1
        
        result = OutlierResult(
            method='iqr',
            outlier_mask=mask,
            count=int(mask.sum()),
            percentage=mask.mean() * 100,
            bounds={
                'q1': q1,
                'q3': q3,
                'iqr': iqr_val,
                'lower': q1 - k * iqr_val,
                'upper': q3 + k * iqr_val
            },
            notes=f"IQR method with k={k}"
        )
        self.results['iqr'] = result
        return result

    # ========================================================================
    # METHOD 5: PERCENTILE (Production-ready, constant review rate)
    # ========================================================================
    
    def percentile(self, lower_pct: float = 1.0, upper_pct: float = 99.0) -> OutlierResult:
        """
        Percentile-based outlier detection.
        
        RECOMMENDED FOR PRODUCTION: Guarantees a constant percentage 
        of items for review, making resource planning predictable.
        
        Args:
            lower_pct: Lower percentile threshold (default: 1, meaning P1)
            upper_pct: Upper percentile threshold (default: 99, meaning P99)
            
        Returns:
            OutlierResult with outlier mask and stats
            
        Example:
            >>> # Flag top 1% of errors for review
            >>> result = detector.percentile(lower_pct=0, upper_pct=99)
            
            >>> # Flag both tails (bottom 2.5% and top 2.5%)
            >>> result = detector.percentile(lower_pct=2.5, upper_pct=97.5)
        """
        def _pct_func(group, lower_pct=1.0, upper_pct=99.0):
            lower = group.quantile(lower_pct / 100)
            upper = group.quantile(upper_pct / 100)
            return pd.Series((group < lower) | (group > upper), index=group.index)
        
        mask = self._apply_grouped(_pct_func, lower_pct=lower_pct, upper_pct=upper_pct)
        mask = mask.fillna(False).astype(bool)
        
        lower_val = self.df[self.value_col].quantile(lower_pct / 100)
        upper_val = self.df[self.value_col].quantile(upper_pct / 100)
        
        result = OutlierResult(
            method='percentile',
            outlier_mask=mask,
            count=int(mask.sum()),
            percentage=mask.mean() * 100,
            bounds={
                'lower_pct': lower_pct,
                'upper_pct': upper_pct,
                'lower_value': lower_val,
                'upper_value': upper_val
            },
            notes=f"Percentile thresholds: P{lower_pct} to P{upper_pct}. "
                  f"Guarantees ~{100 - upper_pct + lower_pct}% flagged."
        )
        self.results['percentile'] = result
        return result
    
    def percentile_upper_only(self, upper_pct: float = 99.0) -> OutlierResult:
        """
        Flag only upper tail outliers (high error values).
        
        For error metrics where low values are always good, only flag
        the high end of the distribution.
        
        Args:
            upper_pct: Upper percentile threshold (default: 99)
            
        Returns:
            OutlierResult with outlier mask and stats
        """
        def _pct_upper_func(group, upper_pct=99.0):
            threshold = group.quantile(upper_pct / 100)
            return pd.Series(group > threshold, index=group.index)
        
        mask = self._apply_grouped(_pct_upper_func, upper_pct=upper_pct)
        mask = mask.fillna(False).astype(bool)
        
        threshold = self.df[self.value_col].quantile(upper_pct / 100)
        
        result = OutlierResult(
            method='percentile_upper',
            outlier_mask=mask,
            count=int(mask.sum()),
            percentage=mask.mean() * 100,
            bounds={
                'upper_pct': upper_pct,
                'threshold': threshold
            },
            notes=f"Upper tail only: values > P{upper_pct} ({threshold:.4f})"
        )
        self.results['percentile_upper'] = result
        return result

    # ========================================================================
    # METHOD 6: ISOLATION FOREST (ML-based, multivariate capable)
    # ========================================================================
    
    def isolation_forest(self, contamination: float = 0.05, 
                         n_estimators: int = 100,
                         additional_cols: Optional[List[str]] = None) -> OutlierResult:
        """
        Isolation Forest anomaly detection.
        
        ML-based method that works by isolating observations. Outliers
        are easier to isolate, requiring fewer random splits.
        
        Args:
            contamination: Expected proportion of outliers (default: 0.05)
            n_estimators: Number of trees (default: 100)
            additional_cols: Optional list of additional columns for 
                           multivariate detection
            
        Returns:
            OutlierResult with outlier mask and stats
            
        Note:
            Requires scikit-learn: pip install scikit-learn
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            raise ImportError("scikit-learn required: pip install scikit-learn")
        
        cols = [self.value_col]
        if additional_cols:
            cols.extend(additional_cols)
        
        # Prepare features
        X = self.df[cols].copy()
        for c in cols:
            X[c] = pd.to_numeric(X[c], errors='coerce')
        X = X.fillna(X.median())
        
        iso = IsolationForest(
            contamination=contamination, 
            n_estimators=n_estimators,
            random_state=42
        )
        predictions = iso.fit_predict(X.values)
        mask = pd.Series(predictions == -1, index=self.df.index)
        
        result = OutlierResult(
            method='isolation_forest',
            outlier_mask=mask,
            count=int(mask.sum()),
            percentage=mask.mean() * 100,
            notes=f"Isolation Forest with contamination={contamination}, "
                  f"features={cols}"
        )
        self.results['isolation_forest'] = result
        return result

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def detect_all(self, skip_ml: bool = False) -> Dict[str, OutlierResult]:
        """
        Run all detection methods.
        
        Args:
            skip_ml: Skip ML-based methods like Isolation Forest
            
        Returns:
            Dictionary of all OutlierResults
        """
        self.log_sigma()
        self.asymmetric_mad()
        self.asymmetric_sigma()
        self.iqr()
        self.percentile()
        self.percentile_upper_only()
        
        if not skip_ml:
            try:
                self.isolation_forest()
            except ImportError:
                logger.warning("scikit-learn not installed, skipping Isolation Forest")
        
        return self.results
    
    def consensus(self, min_methods: int = 2, 
                  methods: Optional[List[str]] = None) -> pd.Series:
        """
        Get consensus outliers flagged by multiple methods.
        
        Args:
            min_methods: Minimum number of methods that must flag a point
            methods: List of method names to include (default: all)
            
        Returns:
            Boolean Series indicating consensus outliers
        """
        if not self.results:
            self.detect_all()
        
        if methods is None:
            methods = list(self.results.keys())
        
        # Stack all masks
        masks = [self.results[m].outlier_mask for m in methods if m in self.results]
        if not masks:
            return pd.Series(False, index=self.df.index)
        
        combined = pd.concat(masks, axis=1).sum(axis=1)
        return combined >= min_methods
    
    def summary(self) -> pd.DataFrame:
        """Get summary DataFrame of all detection results."""
        if not self.results:
            self.detect_all()
        
        rows = []
        for name, result in self.results.items():
            rows.append({
                'Method': name,
                'Outliers': result.count,
                'Percentage': f"{result.percentage:.2f}%",
                'Notes': result.notes
            })
        return pd.DataFrame(rows)
    
    def get_outliers(self, method: str = 'log_sigma') -> pd.DataFrame:
        """
        Get DataFrame of outlier records.
        
        Args:
            method: Detection method to use
            
        Returns:
            DataFrame containing only the outlier rows
        """
        if method not in self.results:
            if method == 'log_sigma':
                self.log_sigma()
            else:
                raise ValueError(f"Method {method} not found. Run detect_all() first.")
        
        mask = self.results[method].outlier_mask
        return self.df[mask].copy()


# ============================================================================
# STANDALONE FUNCTIONS (for quick use without class)
# ============================================================================

def detect_outliers_log_sigma(series: pd.Series, k: float = 3.0) -> pd.Series:
    """
    Quick log-transform + sigma outlier detection.
    
    Args:
        series: Numeric series to analyze
        k: Sigma threshold (default: 3)
        
    Returns:
        Boolean Series marking outliers
    """
    log_vals = np.log(series.replace(0, np.nan))
    mean, std = log_vals.mean(), log_vals.std()
    return ((log_vals < mean - k * std) | (log_vals > mean + k * std)).fillna(False)


def detect_outliers_percentile(series: pd.Series, upper_pct: float = 99.0) -> pd.Series:
    """
    Quick percentile-based outlier detection (upper tail only).
    
    Args:
        series: Numeric series to analyze
        upper_pct: Percentile threshold (default: 99)
        
    Returns:
        Boolean Series marking outliers
    """
    threshold = series.quantile(upper_pct / 100)
    return series > threshold


def detect_outliers_asymmetric_mad(series: pd.Series, threshold: float = 3.5) -> pd.Series:
    """
    Quick asymmetric MAD outlier detection.
    
    Args:
        series: Numeric series to analyze
        threshold: Modified Z-score threshold (default: 3.5)
        
    Returns:
        Boolean Series marking outliers
    """
    median = series.median()
    below = series[series <= median]
    above = series[series >= median]
    
    mad_lower = (median - below).median() if len(below) > 0 else series.std() * 0.6745
    mad_upper = (above - median).median() if len(above) > 0 else series.std() * 0.6745
    
    if mad_lower == 0:
        mad_lower = series.std() * 0.6745
    if mad_upper == 0:
        mad_upper = series.std() * 0.6745
    
    z_lower = np.where(series < median, 0.6745 * (median - series) / mad_lower, 0)
    z_upper = np.where(series > median, 0.6745 * (series - median) / mad_upper, 0)
    
    return pd.Series((z_lower > threshold) | (z_upper > threshold), index=series.index)


# ============================================================================
# DEMO / MAIN
# ============================================================================

if __name__ == "__main__":
    # Demo with sample data
    np.random.seed(42)
    
    # Generate skewed data similar to error metrics
    n = 1000
    data = np.random.lognormal(mean=-1, sigma=0.7, size=n)
    # Add some outliers
    data[:20] = data[:20] * 5
    
    df = pd.DataFrame({
        'error': data,
        'group': np.random.choice(['A', 'B', 'C'], size=n)
    })
    
    print("=" * 60)
    print("OUTLIER DETECTION DEMO")
    print("=" * 60)
    print(f"\nData: n={len(df)}, skewness={df['error'].skew():.2f}")
    
    # Initialize detector
    detector = OutlierDetector(df, 'error', 'group')
    
    # Run all methods
    detector.detect_all()
    
    # Print summary
    print("\n" + detector.summary().to_string(index=False))
    
    # Get consensus outliers
    consensus = detector.consensus(min_methods=3)
    print(f"\nConsensus outliers (≥3 methods): {consensus.sum()} ({consensus.mean()*100:.2f}%)")
    
    # Show top outliers
    print("\nTop 5 outliers:")
    outliers = detector.get_outliers('log_sigma')
    print(outliers.nlargest(5, 'error')[['error', 'group']].to_string())

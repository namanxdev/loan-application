# -*- coding: utf-8 -*-
"""
Decision Agents - 6 AI Agents for Loan Processing

Each agent evaluates a specific aspect of the loan application:
1. AgentAlpha - Sales Validation
2. AgentBeta - KYC Verification  
3. AgentGamma - Credit Risk Assessment
4. AgentDelta - Income Analysis
5. AgentEpsilon - Fraud Detection
6. AgentZeta - Final Sanction Decision

Plus 2 Utility Agents:
- QueryCleanerAgent - Pre-processing
- ResponseFormatterAgent - Post-processing
"""

import re
import random
import time
from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel
from enum import Enum


class AgentDecision(str, Enum):
    """Possible decisions from an agent"""
    APPROVE = "approve"
    REJECT = "reject"
    REVIEW = "review"


class AgentResult(BaseModel):
    """Result from agent evaluation"""
    agent_name: str
    display_name: str
    agent_type: str
    score: int
    decision: AgentDecision
    confidence: int
    explanation: str
    details: Dict[str, Any]
    processing_time_ms: int = 0


# ============== Agent Alpha - Sales Validation ==============

class AgentAlpha:
    """
    Sales Validation Agent
    
    Validates:
    - Application completeness
    - Loan amount vs income ratio
    - Tenure validity
    - Document format requirements
    """
    name = "AgentAlpha"
    display_name = "Sales Validator"
    agent_type = "sales_validation"
    
    def evaluate(self, application: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        score = 100
        issues = []
        details = {}
        
        # Validate loan amount vs income ratio
        loan_amount = application.get("loan_amount", 0)
        income = application.get("income", 0)
        
        if income > 0:
            annual_income = income * 12
            ratio = loan_amount / annual_income
            details["loan_to_income_ratio"] = round(ratio, 2)
            
            if ratio > 5:
                score -= 30
                issues.append(f"Loan amount is {ratio:.1f}x annual income (recommended max 5x)")
            elif ratio > 4:
                score -= 15
                issues.append(f"Loan amount is {ratio:.1f}x annual income (slightly high)")
        else:
            score -= 40
            issues.append("Income information not provided")
        
        # Validate tenure
        tenure = application.get("tenure", 0)
        details["tenure_months"] = tenure
        
        if tenure < 6:
            score -= 25
            issues.append("Tenure too short (minimum 6 months)")
        elif tenure > 360:
            score -= 15
            issues.append("Tenure exceeds 30 years maximum")
        
        # Validate loan amount range
        if loan_amount < 10000:
            score -= 30
            issues.append(f"Loan amount Rs.{loan_amount:,} below minimum Rs.10,000")
        elif loan_amount > 50000000:
            score -= 20
            issues.append(f"Loan amount Rs.{loan_amount:,} exceeds Rs.5 Crore limit")
        
        details["loan_amount"] = loan_amount
        
        # Determine decision
        if score >= 70:
            decision = AgentDecision.APPROVE
        elif score >= 50:
            decision = AgentDecision.REVIEW
        else:
            decision = AgentDecision.REJECT
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            display_name=self.display_name,
            agent_type=self.agent_type,
            score=max(0, score),
            decision=decision,
            confidence=min(95, score),
            explanation="; ".join(issues) if issues else "Application validated successfully",
            details=details,
            processing_time_ms=processing_time
        )


# ============== Agent Beta - KYC Verification ==============

class AgentBeta:
    """
    KYC Verification Agent
    
    Validates:
    - PAN format and checksum
    - Aadhaar format validation
    - Phone number validation
    - Cross-references documents
    """
    name = "AgentBeta"
    display_name = "KYC Verifier"
    agent_type = "kyc_verification"
    
    def evaluate(self, application: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        score = 100
        issues = []
        details = {}
        
        # Validate PAN format
        pan = application.get("pan", "")
        pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
        
        if not pan:
            score -= 40
            issues.append("PAN number not provided")
            details["pan_verified"] = False
        elif not re.match(pan_pattern, pan.upper()):
            score -= 40
            issues.append(f"Invalid PAN format: {pan}")
            details["pan_verified"] = False
        else:
            details["pan_verified"] = True
            details["pan_type"] = self._get_pan_type(pan)
        
        # Validate Aadhaar format
        aadhaar = application.get("aadhaar", "")
        clean_aadhaar = re.sub(r'[\s-]', '', aadhaar)
        
        if not clean_aadhaar:
            score -= 40
            issues.append("Aadhaar number not provided")
            details["aadhaar_verified"] = False
        elif not clean_aadhaar.isdigit() or len(clean_aadhaar) != 12:
            score -= 40
            issues.append("Invalid Aadhaar format (must be 12 digits)")
            details["aadhaar_verified"] = False
        else:
            # Verhoeff checksum would be validated here in production
            details["aadhaar_verified"] = True
            details["aadhaar_masked"] = f"XXXX-XXXX-{clean_aadhaar[-4:]}"
        
        # Validate phone
        phone = application.get("mobile", "")
        clean_phone = re.sub(r'[\s-]', '', phone)
        
        if clean_phone and clean_phone.isdigit() and len(clean_phone) == 10:
            details["phone_verified"] = True
        else:
            score -= 20
            issues.append("Invalid phone number format")
            details["phone_verified"] = False
        
        # Simulate API verification delay (in production, call actual APIs)
        # time.sleep(0.5)  # Uncomment for realistic delay
        
        # Determine decision
        if score >= 70:
            decision = AgentDecision.APPROVE
        elif score >= 50:
            decision = AgentDecision.REVIEW
        else:
            decision = AgentDecision.REJECT
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            display_name=self.display_name,
            agent_type=self.agent_type,
            score=max(0, score),
            decision=decision,
            confidence=min(98, score),
            explanation="; ".join(issues) if issues else "KYC verification successful",
            details=details,
            processing_time_ms=processing_time
        )
    
    def _get_pan_type(self, pan: str) -> str:
        """Determine PAN holder type from 4th character"""
        pan_types = {
            'P': 'Individual',
            'C': 'Company',
            'H': 'HUF',
            'A': 'AOP',
            'B': 'BOI',
            'G': 'Government',
            'J': 'Artificial Juridical Person',
            'L': 'Local Authority',
            'F': 'Firm',
            'T': 'Trust'
        }
        return pan_types.get(pan[3].upper(), 'Unknown')


# ============== Agent Gamma - Credit Risk ==============

class AgentGamma:
    """
    Credit Risk Assessment Agent
    
    Evaluates:
    - Simulated credit score lookup
    - Debt-to-income ratio
    - EMI burden calculation
    - Repayment capacity
    """
    name = "AgentGamma"
    display_name = "Credit Analyst"
    agent_type = "credit_risk"
    
    def evaluate(self, application: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        score = 100
        issues = []
        details = {}
        
        # Simulate credit score lookup (300-900 range in India)
        # In production, this would call CIBIL/Experian API
        credit_score = self._simulate_credit_score(application)
        details["credit_score"] = credit_score
        
        if credit_score < 550:
            score -= 50
            issues.append(f"Very low credit score: {credit_score} (min 550 recommended)")
        elif credit_score < 650:
            score -= 30
            issues.append(f"Low credit score: {credit_score} (650+ preferred)")
        elif credit_score < 700:
            score -= 15
            issues.append(f"Below average credit score: {credit_score}")
        else:
            details["credit_rating"] = "Good" if credit_score >= 750 else "Fair"
        
        # Calculate EMI burden
        loan_amount = application.get("loan_amount", 0)
        tenure = application.get("tenure", 12)
        income = application.get("income", 1)
        
        # Calculate EMI using reducing balance method
        annual_rate = 12.0  # 12% annual interest rate
        monthly_rate = annual_rate / 12 / 100
        
        if tenure > 0 and monthly_rate > 0:
            emi = (loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure)) / (((1 + monthly_rate) ** tenure) - 1)
        else:
            emi = loan_amount / max(tenure, 1)
        
        emi_ratio = (emi / income) * 100 if income > 0 else 100
        
        details["estimated_emi"] = int(emi)
        details["emi_to_income_ratio"] = round(emi_ratio, 1)
        
        if emi_ratio > 60:
            score -= 35
            issues.append(f"EMI burden too high: {emi_ratio:.1f}% of income (max 60%)")
        elif emi_ratio > 50:
            score -= 20
            issues.append(f"EMI burden elevated: {emi_ratio:.1f}% of income")
        elif emi_ratio > 40:
            score -= 10
            issues.append(f"Moderate EMI burden: {emi_ratio:.1f}% of income")
        
        # Fixed Obligations to Income Ratio (FOIR) estimate
        foir = emi_ratio  # In production, include other EMIs
        details["foir"] = round(foir, 1)
        
        # Determine decision
        if score >= 70:
            decision = AgentDecision.APPROVE
        elif score >= 50:
            decision = AgentDecision.REVIEW
        else:
            decision = AgentDecision.REJECT
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            display_name=self.display_name,
            agent_type=self.agent_type,
            score=max(0, score),
            decision=decision,
            confidence=min(90, score),
            explanation="; ".join(issues) if issues else f"Credit assessment passed. Score: {credit_score}",
            details=details,
            processing_time_ms=processing_time
        )
    
    def _simulate_credit_score(self, application: Dict[str, Any]) -> int:
        """Simulate credit score based on application data"""
        # Base score
        base_score = 700
        
        # Income factor
        income = application.get("income", 0)
        if income >= 100000:
            base_score += 50
        elif income >= 50000:
            base_score += 30
        elif income >= 25000:
            base_score += 10
        elif income < 15000:
            base_score -= 50
        
        # Add some randomness to simulate real-world variance
        variance = random.randint(-50, 50)
        
        return max(300, min(900, base_score + variance))


# ============== Agent Delta - Income Analysis ==============

class AgentDelta:
    """
    Income Analysis Agent
    
    Verifies:
    - Income stability
    - Employment type assessment
    - Minimum income thresholds
    - Income documentation
    """
    name = "AgentDelta"
    display_name = "Income Analyzer"
    agent_type = "income_analysis"
    
    def evaluate(self, application: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        score = 100
        issues = []
        details = {}
        
        income = application.get("income", 0)
        loan_amount = application.get("loan_amount", 0)
        
        details["declared_income"] = income
        details["currency"] = "INR"
        
        # Minimum income check
        if income <= 0:
            score -= 50
            issues.append("No income information provided")
        elif income < 15000:
            score -= 40
            issues.append(f"Income Rs.{income:,}/month below minimum Rs.15,000")
        elif income < 25000:
            score -= 20
            issues.append(f"Income Rs.{income:,}/month is on lower side")
        elif income < 35000:
            score -= 10
            issues.append(f"Moderate income level: Rs.{income:,}/month")
        else:
            details["income_category"] = "Good" if income >= 50000 else "Adequate"
        
        # Annual income calculation
        annual_income = income * 12
        details["annual_income"] = annual_income
        
        # Loan affordability check
        max_loan_recommended = annual_income * 5
        details["max_loan_recommended"] = max_loan_recommended
        
        if loan_amount > max_loan_recommended:
            affordability_gap = loan_amount - max_loan_recommended
            score -= 15
            issues.append(f"Loan exceeds recommended limit by Rs.{affordability_gap:,}")
        
        # Income stability indicator (simulated)
        # In production, this would analyze bank statements, ITR
        stability_score = random.randint(70, 100)
        details["income_stability_score"] = stability_score
        
        if stability_score < 75:
            score -= 15
            issues.append("Income stability appears lower than preferred")
        
        # Determine decision
        if score >= 70:
            decision = AgentDecision.APPROVE
        elif score >= 50:
            decision = AgentDecision.REVIEW
        else:
            decision = AgentDecision.REJECT
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            display_name=self.display_name,
            agent_type=self.agent_type,
            score=max(0, score),
            decision=decision,
            confidence=min(85, score),
            explanation="; ".join(issues) if issues else f"Income verified: Rs.{income:,}/month",
            details=details,
            processing_time_ms=processing_time
        )


# ============== Agent Epsilon - Fraud Detection ==============

class AgentEpsilon:
    """
    Fraud Detection Agent
    
    Checks for:
    - Suspicious patterns
    - Document authenticity markers
    - Velocity checks
    - Known fraud indicators
    """
    name = "AgentEpsilon"
    display_name = "Fraud Detector"
    agent_type = "fraud_detection"
    
    def evaluate(self, application: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        score = 100
        risk_flags = []
        details = {}
        
        # Initialize fraud score (higher is safer)
        fraud_score = 100
        
        # Check for common fraud patterns
        # Pattern 1: Round numbers in income (less likely to be accurate)
        income = application.get("income", 0)
        if income > 0 and income % 10000 == 0:
            fraud_score -= 5
            details["round_income_flag"] = True
        else:
            details["round_income_flag"] = False
        
        # Pattern 2: Very high loan for low income
        loan_amount = application.get("loan_amount", 0)
        if income > 0 and loan_amount > income * 100:
            fraud_score -= 30
            risk_flags.append("Unusual loan-to-income ratio detected")
        
        # Pattern 3: Simulated device/behavior fingerprinting
        # In production, check device fingerprint, IP, etc.
        velocity_check = random.random()
        details["velocity_score"] = int(velocity_check * 100)
        
        if velocity_check > 0.95:
            fraud_score -= 40
            risk_flags.append("Multiple applications detected from same source")
        elif velocity_check > 0.85:
            fraud_score -= 20
            risk_flags.append("Elevated application velocity")
        
        # Pattern 4: Document anomaly check (simulated)
        doc_score = random.randint(70, 100)
        details["document_score"] = doc_score
        
        if doc_score < 75:
            fraud_score -= 25
            risk_flags.append("Document anomalies detected - manual review needed")
        
        # Pattern 5: Known fraud database check (simulated)
        blacklist_hit = random.random() > 0.98  # 2% chance
        details["blacklist_clear"] = not blacklist_hit
        
        if blacklist_hit:
            fraud_score = 10
            risk_flags.append("Match found in fraud database - HIGH RISK")
        
        # Calculate final score
        score = fraud_score
        details["fraud_risk_score"] = 100 - fraud_score  # Invert for risk display
        
        # Determine decision
        if score >= 70:
            decision = AgentDecision.APPROVE
        elif score >= 50:
            decision = AgentDecision.REVIEW
        else:
            decision = AgentDecision.REJECT
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            display_name=self.display_name,
            agent_type=self.agent_type,
            score=max(0, score),
            decision=decision,
            confidence=min(92, score),
            explanation="; ".join(risk_flags) if risk_flags else "No fraud indicators detected",
            details=details,
            processing_time_ms=processing_time
        )


# ============== Agent Zeta - Sanction Decision ==============

class AgentZeta:
    """
    Final Sanction Decision Agent
    
    Aggregates all agent results and makes final decision:
    - Compiles scores from all agents
    - Applies business rules
    - Generates final verdict
    - Triggers sanction letter generation
    """
    name = "AgentZeta"
    display_name = "Sanction Authority"
    agent_type = "sanction_decision"
    
    def evaluate(self, application: Dict[str, Any], all_results: List[AgentResult]) -> AgentResult:
        start_time = time.time()
        details = {}
        
        # Aggregate scores from all agents
        if all_results:
            total_score = sum(r.score for r in all_results) / len(all_results)
            weighted_score = self._calculate_weighted_score(all_results)
        else:
            total_score = 0
            weighted_score = 0
        
        details["average_score"] = round(total_score, 1)
        details["weighted_score"] = round(weighted_score, 1)
        details["total_agents"] = len(all_results)
        
        # Check for any rejections
        rejections = [r for r in all_results if r.decision == AgentDecision.REJECT]
        reviews = [r for r in all_results if r.decision == AgentDecision.REVIEW]
        approvals = [r for r in all_results if r.decision == AgentDecision.APPROVE]
        
        details["rejections"] = len(rejections)
        details["reviews"] = len(reviews)
        details["approvals"] = len(approvals)
        
        # Decision logic
        if rejections:
            # Any rejection = overall rejection
            decision = AgentDecision.REJECT
            rejection_agents = ", ".join(r.display_name for r in rejections)
            explanation = f"Rejected by: {rejection_agents}"
            score = min(r.score for r in rejections)
        elif len(reviews) >= 2:
            # Multiple reviews = manual review needed
            decision = AgentDecision.REVIEW
            review_agents = ", ".join(r.display_name for r in reviews)
            explanation = f"Manual review required. Flagged by: {review_agents}"
            score = int(weighted_score)
        elif reviews and weighted_score < 70:
            # Single review with low overall score
            decision = AgentDecision.REVIEW
            explanation = f"Borderline case with score {weighted_score:.0f}. Manual review recommended."
            score = int(weighted_score)
        elif weighted_score >= 70:
            # All checks passed
            decision = AgentDecision.APPROVE
            explanation = f"All checks passed. Final score: {weighted_score:.0f}/100. Loan approved."
            score = int(weighted_score)
        else:
            # Low overall score
            decision = AgentDecision.REVIEW
            explanation = f"Score {weighted_score:.0f} below threshold. Manual review required."
            score = int(weighted_score)
        
        # Add agent breakdown to details
        details["agent_breakdown"] = [
            {
                "agent": r.agent_name,
                "display_name": r.display_name,
                "score": r.score,
                "decision": r.decision.value
            }
            for r in all_results
        ]
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_name=self.name,
            display_name=self.display_name,
            agent_type=self.agent_type,
            score=max(0, min(100, score)),
            decision=decision,
            confidence=min(95, int(weighted_score)) if all_results else 0,
            explanation=explanation,
            details=details,
            processing_time_ms=processing_time
        )
    
    def _calculate_weighted_score(self, results: List[AgentResult]) -> float:
        """Calculate weighted average score based on agent importance"""
        weights = {
            "AgentAlpha": 0.15,   # Sales validation
            "AgentBeta": 0.20,    # KYC - important
            "AgentGamma": 0.25,   # Credit risk - most important
            "AgentDelta": 0.15,   # Income
            "AgentEpsilon": 0.25, # Fraud - critical
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for r in results:
            weight = weights.get(r.agent_name, 0.1)
            weighted_sum += r.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0


# ============== Utility Agents ==============

class QueryCleanerAgent:
    """
    Pre-processing agent for chat messages
    
    Functions:
    - Cleans and normalizes input
    - Extracts structured data from text
    - Validates format
    """
    name = "QueryCleaner"
    display_name = "Query Processor"
    
    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process and extract data from user message"""
        cleaned = message.strip()
        extracted = {}
        
        # Extract phone number
        phone_match = re.search(r'\b(\d{10})\b', cleaned)
        if phone_match:
            extracted['mobile'] = phone_match.group(1)
        
        # Extract PAN
        pan_match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', cleaned.upper())
        if pan_match:
            extracted['pan'] = pan_match.group(1)
        
        # Extract Aadhaar (with or without spaces/hyphens)
        aadhaar_clean = re.sub(r'[\s-]', '', cleaned)
        aadhaar_match = re.search(r'\b(\d{12})\b', aadhaar_clean)
        if aadhaar_match:
            extracted['aadhaar'] = aadhaar_match.group(1)
        
        # Extract amounts (lakhs/lacs format)
        amount_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakhs?|lacs?|L)\b', cleaned, re.I)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            extracted['loan_amount'] = int(float(amount_str) * 100000)
        else:
            # Try plain number for larger amounts
            plain_amount = re.search(r'(?:rs\.?|₹)?\s*(\d{5,8})\b', cleaned, re.I)
            if plain_amount:
                extracted['loan_amount'] = int(plain_amount.group(1))
        
        # Extract tenure (months/years)
        tenure_months = re.search(r'(\d+)\s*(?:months?|mo)\b', cleaned, re.I)
        tenure_years = re.search(r'(\d+)\s*(?:years?|yrs?)\b', cleaned, re.I)
        
        if tenure_months:
            extracted['tenure'] = int(tenure_months.group(1))
        elif tenure_years:
            extracted['tenure'] = int(tenure_years.group(1)) * 12
        
        # Extract income
        income_match = re.search(r'(?:income|salary|earning)[^\d]*(\d+(?:,\d+)*)', cleaned, re.I)
        if income_match:
            extracted['income'] = int(income_match.group(1).replace(',', ''))
        
        # Extract name (if mentioned with "name is" or "I am")
        name_match = re.search(r'(?:name is|i am|this is|i\'m)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)', cleaned, re.I)
        if name_match:
            extracted['customer_name'] = name_match.group(1).title()
        
        return {
            "cleaned_message": cleaned,
            "extracted_data": extracted,
            "original_message": message,
            "extraction_count": len(extracted)
        }


class ResponseFormatterAgent:
    """
    Post-processing agent for responses
    
    Functions:
    - Formats agent responses for display
    - Adds emoji and context
    - Humanizes technical output
    """
    name = "ResponseFormatter"
    display_name = "Response Formatter"
    
    TEMPLATES = {
        "AgentAlpha": "📋 **Sales Review**: {explanation}",
        "AgentBeta": "🔍 **KYC Check**: {explanation}",
        "AgentGamma": "📊 **Credit Analysis**: {explanation}",
        "AgentDelta": "💰 **Income Review**: {explanation}",
        "AgentEpsilon": "🛡️ **Security Check**: {explanation}",
        "AgentZeta": "✅ **Final Decision**: {explanation}"
    }
    
    def format(self, agent_result: AgentResult, context: Dict[str, Any] = None) -> str:
        """Format agent result for display"""
        template = self.TEMPLATES.get(
            agent_result.agent_name, 
            "🤖 **{display_name}**: {explanation}"
        )
        
        return template.format(
            explanation=agent_result.explanation,
            display_name=agent_result.display_name
        )
    
    def format_summary(self, results: List[AgentResult]) -> str:
        """Format summary of all agent results"""
        lines = ["## Application Assessment Summary\n"]
        
        for result in results:
            status_emoji = "✅" if result.decision == AgentDecision.APPROVE else (
                "⚠️" if result.decision == AgentDecision.REVIEW else "❌"
            )
            lines.append(
                f"{status_emoji} **{result.display_name}**: "
                f"Score {result.score}/100 - {result.explanation}"
            )
        
        return "\n".join(lines)


# Singleton instances for easy import
agent_alpha = AgentAlpha()
agent_beta = AgentBeta()
agent_gamma = AgentGamma()
agent_delta = AgentDelta()
agent_epsilon = AgentEpsilon()
agent_zeta = AgentZeta()
query_cleaner = QueryCleanerAgent()
response_formatter = ResponseFormatterAgent()


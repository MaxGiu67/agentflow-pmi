"""Re-export all models so `from api.db.models import Base, User, CrmDeal` still works."""

from api.db.models.base import Base

from api.db.models.auth import (
    Tenant,
    TenantUsage,
    TenantSetting,
    User,
    OnboardingState,
)

from api.db.models.accounting import (
    Invoice,
    AgentEvent,
    CategorizationFeedback,
    JournalEntry,
    JournalLine,
    ChartAccount,
    ActiveInvoice,
    BankConnection,
    BankAccount,
    BankTransaction,
    BankStatementImport,
    Reconciliation,
    Accrual,
)

from api.db.models.fiscal import (
    FiscalRule,
    VatSettlement,
    FiscalDeadline,
    WithholdingTax,
    StampDuty,
    CertificazioneUnica,
    F24Document,
    F24Versamento,
)

from api.db.models.crm import (
    CrmCompany,
    CrmContact,
    CrmPipelineStage,
    CrmDeal,
    CrmActivity,
    CrmDealDocument,
    CrmDealProduct,
    CrmDealResource,
)

from api.db.models.crm_config import (
    CrmContactOrigin,
    CrmActivityType,
    CrmRole,
    CrmRolePermission,
    CrmAuditLog,
    CrmProductCategory,
    CrmProduct,
    CrmDashboardWidget,
    CrmCompensationRule,
    CrmCompensationEntry,
)

from api.db.models.pipeline import (
    PipelineTemplate,
    PipelineTemplateStage,
)

from api.db.models.email import (
    EmailTemplate,
    EmailCampaign,
    EmailSend,
    EmailEvent,
    EmailSequenceStep,
    EmailSequenceEnrollment,
)

from api.db.models.pec import (
    TenantPecConfig,
    PecMessage,
)

from api.db.models.scarico_massivo import (
    ScaricoMassivoConfig,
    ScaricoFatturaLog,
)

from api.db.models.other import (
    WebhookEvent,
    NotificationConfig,
    NotificationLog,
    EmailConnection,
    Corrispettivo,
    ImportPromptTemplate,
    ImportException,
    CompletenessScore,
    Expense,
    ExpensePolicy,
    Asset,
    DigitalPreservation,
    Payment,
    NormativeAlert,
    Budget,
    BudgetMeta,
    Scadenza,
    BankFacility,
    InvoiceAdvance,
    Resource,
    ResourceSkill,
    EleviaUseCase,
    AtecoUseCaseMatrix,
    CrossSellSignal,
    DashboardLayout,
    Conversation,
    Message,
    AgentConfig,
    ConversationMemory,
    PayrollCost,
    RecurringContract,
    Loan,
)

__all__ = [
    "Base",
    # auth
    "Tenant", "TenantUsage", "TenantSetting", "User", "OnboardingState",
    # accounting
    "Invoice", "AgentEvent", "CategorizationFeedback", "JournalEntry", "JournalLine",
    "ChartAccount", "ActiveInvoice", "BankAccount", "BankTransaction", "BankStatementImport",
    "Reconciliation", "Accrual",
    # fiscal
    "FiscalRule", "VatSettlement", "FiscalDeadline", "WithholdingTax", "StampDuty",
    "CertificazioneUnica", "F24Document", "F24Versamento",
    # crm
    "CrmCompany", "CrmContact", "CrmPipelineStage", "CrmDeal", "CrmActivity",
    "CrmDealDocument", "CrmDealProduct", "CrmDealResource",
    # crm_config
    "CrmContactOrigin", "CrmActivityType", "CrmRole", "CrmRolePermission", "CrmAuditLog",
    "CrmProductCategory", "CrmProduct", "CrmDashboardWidget",
    "CrmCompensationRule", "CrmCompensationEntry",
    # pipeline
    "PipelineTemplate", "PipelineTemplateStage",
    # email
    "EmailTemplate", "EmailCampaign", "EmailSend", "EmailEvent",
    "EmailSequenceStep", "EmailSequenceEnrollment",
    # pec
    "TenantPecConfig", "PecMessage",
    # scarico massivo
    "ScaricoMassivoConfig", "ScaricoFatturaLog",
    # other
    "NotificationConfig", "NotificationLog", "EmailConnection", "Corrispettivo",
    "ImportPromptTemplate", "ImportException", "CompletenessScore",
    "Expense", "ExpensePolicy", "Asset", "DigitalPreservation", "Payment", "NormativeAlert",
    "Budget", "BudgetMeta", "Scadenza", "BankFacility", "InvoiceAdvance",
    "Resource", "ResourceSkill", "EleviaUseCase", "AtecoUseCaseMatrix", "CrossSellSignal",
    "DashboardLayout", "Conversation", "Message", "AgentConfig", "ConversationMemory",
    "PayrollCost", "RecurringContract", "Loan",
]

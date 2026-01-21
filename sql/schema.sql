/* ============================================================
   SCHEMA INDICADORES - SQL SERVER (compatível com app.py atual)
   Tabelas:
     ZSE - Setores
     ZFU - Funcionários (SEM ZFU_PERFIL)
     ZIN - Indicadores
     ZIV - Valores salvos (upsert por Setor+Indicador+Período)
     ZDR - Drafts (rascunhos)
   ============================================================ */

-- =========================
-- ZSE - SETORES
-- =========================
IF OBJECT_ID('dbo.ZSE', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ZSE (
        ZSE_ID       INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ZSE PRIMARY KEY,
        ZSE_NOME     NVARCHAR(200) NOT NULL,
        ZSE_ATIVO    BIT NOT NULL CONSTRAINT DF_ZSE_ATIVO DEFAULT (1),
        ZSE_CRIADO_EM       DATETIME2(0) NOT NULL CONSTRAINT DF_ZSE_CRIADO DEFAULT (SYSUTCDATETIME()),
        ZSE_ATUALIZADO_EM   DATETIME2(0) NULL
    );

    CREATE UNIQUE INDEX UX_ZSE_NOME ON dbo.ZSE (ZSE_NOME);
END
GO

-- =========================
-- ZFU - FUNCIONÁRIOS
-- (atualizado: SEM ZFU_PERFIL)
-- =========================
IF OBJECT_ID('dbo.ZFU', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ZFU (
        ZFU_ID       INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ZFU PRIMARY KEY,
        ZFU_NOME     NVARCHAR(200) NOT NULL,
        ZFU_EMAIL    NVARCHAR(320) NULL,
        ZFU_SETOR_ID INT NULL,
        ZFU_ATIVO    BIT NOT NULL CONSTRAINT DF_ZFU_ATIVO DEFAULT (1),
        ZFU_CRIADO_EM       DATETIME2(0) NOT NULL CONSTRAINT DF_ZFU_CRIADO DEFAULT (SYSUTCDATETIME()),
        ZFU_ATUALIZADO_EM   DATETIME2(0) NULL,

        CONSTRAINT FK_ZFU_ZSE FOREIGN KEY (ZFU_SETOR_ID) REFERENCES dbo.ZSE(ZSE_ID)
    );

    -- email como identificador estável (permite vários NULLs)
    CREATE UNIQUE INDEX UX_ZFU_EMAIL ON dbo.ZFU (ZFU_EMAIL)
    WHERE ZFU_EMAIL IS NOT NULL;
END
GO

-- =========================
-- ZIN - INDICADORES
-- =========================
IF OBJECT_ID('dbo.ZIN', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ZIN (
        ZIN_ID       INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ZIN PRIMARY KEY,
        ZIN_SETOR_ID INT NOT NULL,
        ZIN_CODIGO   NVARCHAR(50) NOT NULL,   -- código interno por setor (string no app)
        ZIN_NOME     NVARCHAR(400) NOT NULL,
        ZIN_TIPO     NVARCHAR(50) NULL,       -- texto, numero, data...
        ZIN_UNIDADE  NVARCHAR(50) NULL,       -- R$, %, un, etc
        ZIN_META     NVARCHAR(100) NULL,      -- meta (no app vem variado, então string é mais seguro)
        ZIN_ATIVO    BIT NOT NULL CONSTRAINT DF_ZIN_ATIVO DEFAULT (1),
        ZIN_CRIADO_EM       DATETIME2(0) NOT NULL CONSTRAINT DF_ZIN_CRIADO DEFAULT (SYSUTCDATETIME()),
        ZIN_ATUALIZADO_EM   DATETIME2(0) NULL,

        CONSTRAINT FK_ZIN_ZSE FOREIGN KEY (ZIN_SETOR_ID) REFERENCES dbo.ZSE(ZSE_ID)
    );

    -- impede duplicar código dentro do mesmo setor
    CREATE UNIQUE INDEX UX_ZIN_SETOR_CODIGO ON dbo.ZIN (ZIN_SETOR_ID, ZIN_CODIGO);
END
GO

-- =========================
-- ZIV - VALORES (salvos)
-- (o app faz MERGE por: Indicador + Setor + Periodo)
-- =========================
IF OBJECT_ID('dbo.ZIV', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ZIV (
        ZIV_ID             BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ZIV PRIMARY KEY,
        ZIV_INDICADOR_ID   INT NOT NULL,
        ZIV_SETOR_ID       INT NOT NULL,
        ZIV_FUNCIONARIO_ID INT NULL,
        ZIV_PERIODO        DATE NOT NULL,           -- sempre 1º dia do mês no app
        ZIV_VALOR          NVARCHAR(200) NULL,      -- app grava como str(...)
        ZIV_CRIADO_EM      DATETIME2(0) NOT NULL,
        ZIV_ATUALIZADO_EM  DATETIME2(0) NOT NULL,

        CONSTRAINT FK_ZIV_ZIN FOREIGN KEY (ZIV_INDICADOR_ID) REFERENCES dbo.ZIN(ZIN_ID),
        CONSTRAINT FK_ZIV_ZSE FOREIGN KEY (ZIV_SETOR_ID) REFERENCES dbo.ZSE(ZSE_ID),
        CONSTRAINT FK_ZIV_ZFU FOREIGN KEY (ZIV_FUNCIONARIO_ID) REFERENCES dbo.ZFU(ZFU_ID)
    );

    -- garante 1 valor por indicador/setor/período
    CREATE UNIQUE INDEX UX_ZIV_IND_SET_PER ON dbo.ZIV (ZIV_INDICADOR_ID, ZIV_SETOR_ID, ZIV_PERIODO);

    -- ajuda consultas por período/setor (Power BI)
    CREATE INDEX IX_ZIV_SETOR_PERIODO ON dbo.ZIV (ZIV_SETOR_ID, ZIV_PERIODO) INCLUDE (ZIV_INDICADOR_ID, ZIV_VALOR);
END
GO

-- =========================
-- ZDR - DRAFTS (rascunhos)
-- (o app só insere; não faz merge)
-- =========================
IF OBJECT_ID('dbo.ZDR', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ZDR (
        ZDR_ID             BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ZDR PRIMARY KEY,
        ZDR_INDICADOR_ID   INT NOT NULL,
        ZDR_SETOR_ID       INT NOT NULL,
        ZDR_FUNCIONARIO_ID INT NULL,
        ZDR_PERIODO        DATE NOT NULL,          -- sempre 1º dia do mês no app
        ZDR_VALOR          NVARCHAR(200) NULL,
        ZDR_CRIADO_EM      DATETIME2(0) NOT NULL,

        CONSTRAINT FK_ZDR_ZIN FOREIGN KEY (ZDR_INDICADOR_ID) REFERENCES dbo.ZIN(ZIN_ID),
        CONSTRAINT FK_ZDR_ZSE FOREIGN KEY (ZDR_SETOR_ID) REFERENCES dbo.ZSE(ZSE_ID),
        CONSTRAINT FK_ZDR_ZFU FOREIGN KEY (ZDR_FUNCIONARIO_ID) REFERENCES dbo.ZFU(ZFU_ID)
    );

    CREATE INDEX IX_ZDR_SETOR_PERIODO ON dbo.ZDR (ZDR_SETOR_ID, ZDR_PERIODO) INCLUDE (ZDR_INDICADOR_ID, ZDR_VALOR, ZDR_CRIADO_EM);
END
GO

/* ============================================================
   BLOCO OPCIONAL: se suas tabelas já existem, garante colunas mínimas
   (não remove nada; só adiciona o que faltar)
   ============================================================ */

-- ZFU: garante que NÃO precisamos de ZFU_PERFIL (o app não usa)
-- (Se quiser PERFIL no futuro, adicione: ALTER TABLE dbo.ZFU ADD ZFU_PERFIL NVARCHAR(50) NULL;)

-- Garantir colunas essenciais (exemplo):
IF COL_LENGTH('dbo.ZFU', 'ZFU_ATIVO') IS NULL
    ALTER TABLE dbo.ZFU ADD ZFU_ATIVO BIT NOT NULL CONSTRAINT DF_ZFU_ATIVO2 DEFAULT(1);
GO

IF COL_LENGTH('dbo.ZSE', 'ZSE_ATIVO') IS NULL
    ALTER TABLE dbo.ZSE ADD ZSE_ATIVO BIT NOT NULL CONSTRAINT DF_ZSE_ATIVO2 DEFAULT(1);
GO
 
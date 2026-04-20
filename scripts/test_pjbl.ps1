param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Title = "PjBL Sampah Sekolah",
    [string]$UserEmail = "guru@local",
    [string]$UserDisplayName = "Guru Lokal"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-JsonPost {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [Parameter(Mandatory = $true)]
        [hashtable]$Body
    )

    return Invoke-RestMethod `
        -Uri $Url `
        -Method Post `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 20)
}

function Invoke-JsonPatch {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [Parameter(Mandatory = $true)]
        [hashtable]$Body
    )

    return Invoke-RestMethod `
        -Uri $Url `
        -Method Patch `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 20)
}

Write-Host "1. Membuat session PJBL..." -ForegroundColor Cyan

$createBody = @{
    title = $Title
    workflow_type = "pjbl"
    user_email = $UserEmail
    user_display_name = $UserDisplayName
}

$session = Invoke-JsonPost -Url "$BaseUrl/api/v1/studio-sessions" -Body $createBody
$sessionId = $session.id

Write-Host "Session ID: $sessionId" -ForegroundColor Green
Write-Host "Stage awal: $($session.planning_state.current_stage)"
Write-Host ""

Write-Host "2. Mengisi Stage 1..." -ForegroundColor Cyan

$stage1 = @{
    collected_fields = @{
        education_level = "SMP"
        phase = "D"
        grade_level = "Kelas 8"
        subject_or_theme = "IPA Terpadu"
        topic = "Pengelolaan Sampah Sekolah"
        duration = "4 minggu"
        school_context = "Sekolah memiliki area kantin aktif dan program bank sampah sederhana."
        student_characteristics = @(
            "Kolaboratif"
            "Perlu penguatan observasi lapangan"
        )
        project_theme = "Sekolah minim sampah"
    }
}

$r1 = Invoke-JsonPatch -Url "$BaseUrl/api/v1/studio-sessions/$sessionId/planning-state" -Body $stage1
Write-Host "Stage sekarang: $($r1.planning_state.current_stage)"
Write-Host "Missing fields: $($r1.planning_state.missing_fields -join ', ')"
Write-Host ""

Write-Host "3. Mengisi Stage 2..." -ForegroundColor Cyan

$stage2 = @{
    collected_fields = @{
        problem_context = "Volume sampah plastik di area kantin meningkat setiap minggu."
        project_objectives = @(
            "Menganalisis sumber sampah utama"
            "Merancang solusi pengurangan sampah plastik"
        )
        target_competencies = @(
            "Bernalar kritis"
            "Kolaborasi"
            "Komunikasi ilmiah"
        )
        character_values = @(
            "Gotong royong"
            "Tanggung jawab"
        )
        six_c_elements = @(
            "Critical thinking"
            "Collaboration"
            "Citizenship"
        )
    }
}

$r2 = Invoke-JsonPatch -Url "$BaseUrl/api/v1/studio-sessions/$sessionId/planning-state" -Body $stage2
Write-Host "Stage sekarang: $($r2.planning_state.current_stage)"
Write-Host "Missing fields: $($r2.planning_state.missing_fields -join ', ')"
Write-Host ""

Write-Host "4. Mengisi Stage 3..." -ForegroundColor Cyan

$stage3 = @{
    collected_fields = @{
        project_title = "Sekolah Minim Sampah Plastik"
        driving_question = "Bagaimana siswa dapat menurunkan sampah plastik kantin secara terukur?"
        project_stages = @(
            "Observasi kondisi awal"
            "Analisis data sampah"
            "Desain solusi"
            "Presentasi hasil"
        )
        grouping_strategy = "Kelompok 4-5 siswa dengan peran campuran."
        student_roles = @(
            "Ketua tim"
            "Pencatat data"
            "Desainer kampanye"
            "Presenter"
        )
        final_product = "Proposal aksi sekolah dan media kampanye pengurangan sampah."
    }
}

$r3 = Invoke-JsonPatch -Url "$BaseUrl/api/v1/studio-sessions/$sessionId/planning-state" -Body $stage3
Write-Host "Stage sekarang: $($r3.planning_state.current_stage)"
Write-Host "Ready for summary: $($r3.planning_state.is_ready_for_summary)"
Write-Host "Ready for generation: $($r3.planning_state.is_ready_for_generation)"
Write-Host ""

Write-Host "5. Mengisi Stage 4..." -ForegroundColor Cyan

$stage4 = @{
    collected_fields = @{
        assessment_focus = @(
            "Kualitas analisis data"
            "Kualitas solusi"
            "Kolaborasi tim"
        )
        assessment_rubric = @{
            analisis = "Akurat, berbasis data, dan relevan dengan konteks sekolah"
            solusi = "Realistis, kreatif, dan dapat diterapkan"
        }
        process_indicators = @(
            "Mampu mengumpulkan data lapangan"
            "Mampu membagi tugas secara adil"
        )
        product_indicators = @(
            "Proposal memuat langkah aksi yang jelas"
            "Media kampanye mudah dipahami"
        )
        resources_needed = @(
            "Data observasi"
            "Akses area kantin"
            "Contoh media kampanye"
        )
        tools_materials = @(
            "Timbangan sederhana"
            "Spreadsheet"
            "Canva"
        )
        teacher_facilitation_plan = "Guru memfasilitasi observasi, validasi ide, dan refleksi mingguan."
        reflection_prompt = "Apa perubahan kebiasaan yang paling realistis untuk diterapkan di sekolah?"
        follow_up_plan = "Hasil proyek dibawa ke rapat OSIS dan dipantau selama 1 bulan."
    }
}

$r4 = Invoke-JsonPatch -Url "$BaseUrl/api/v1/studio-sessions/$sessionId/planning-state" -Body $stage4
Write-Host "Stage sekarang: $($r4.planning_state.current_stage)"
Write-Host "Completion score: $($r4.planning_state.completion_score)"
Write-Host "Ready for summary: $($r4.planning_state.is_ready_for_summary)"
Write-Host "Ready for generation: $($r4.planning_state.is_ready_for_generation)"
Write-Host ""

if (-not $r4.planning_state.is_ready_for_generation) {
    throw "Planning state belum siap untuk finalisasi."
}

Write-Host "6. Finalisasi dan membuat generated document..." -ForegroundColor Cyan

$final = Invoke-JsonPost -Url "$BaseUrl/api/v1/studio-sessions/$sessionId/finalize" -Body @{}

Write-Host ""
Write-Host "=== HASIL FINAL ===" -ForegroundColor Yellow

[pscustomobject]@{
    session_id = $final.session.id
    workflow_type = $final.session.workflow_type
    current_stage = $final.session.planning_state.current_stage
    session_status = $final.session.status
    completion_score = $final.session.planning_state.completion_score
    is_ready_for_summary = $final.session.planning_state.is_ready_for_summary
    is_ready_for_generation = $final.session.planning_state.is_ready_for_generation
    generated_document_id = $final.generated_document.id
    generated_document_kind = $final.generated_document.kind
    generated_document_title = $final.generated_document.title
    generated_document_version = $final.generated_document.version
} | Format-List

Write-Host ""
Write-Host "7. Mengambil detail session terbaru..." -ForegroundColor Cyan

$detail = Invoke-RestMethod -Uri "$BaseUrl/api/v1/studio-sessions/$sessionId" -Method Get

[pscustomobject]@{
    session_id = $detail.id
    generated_documents_count = $detail.generated_documents.Count
    current_stage = $detail.planning_state.current_stage
    missing_fields = ($detail.planning_state.missing_fields -join ", ")
} | Format-List

Write-Host ""
Write-Host "Tes PJBL selesai." -ForegroundColor Green

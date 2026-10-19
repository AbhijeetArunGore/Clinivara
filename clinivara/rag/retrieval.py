"""
Grounded Clinical Document Retrieval and Question Answering Engine.
Enforces evidence sufficiency thresholds and returns INSUFFICIENT_EVIDENCE when unsupported.
"""

from clinivara.ai.guardrails.injection_guard import PromptInjectionGuard
from clinivara.ai.prompts.registry import prompt_registry
from clinivara.ai.providers import get_llm_provider
from clinivara.rag.chunking import ClinicalDocumentChunker
from clinivara.rag.citations import CitationManager
from clinivara.rag.indexing import document_index_manager
from clinivara.schemas.ai import Citation, QuestionAnswerRequest, QuestionAnswerResponse
from clinivara.schemas.approved_output import ApprovedDocumentOutput


class ClinicalRetriever:
    """Answers patient/clinician questions grounded strictly in authorized document evidence."""

    def __init__(self, relevance_threshold: float = 0.15):
        self.relevance_threshold = relevance_threshold
        self.chunker = ClinicalDocumentChunker()
        self.injection_guard = PromptInjectionGuard()
        self.citation_manager = CitationManager()
        self.llm_provider = get_llm_provider()

    def answer_question(
        self,
        tenant_id: str,
        document_id: str,
        approved_doc: ApprovedDocumentOutput,
        request: QuestionAnswerRequest,
    ) -> QuestionAnswerResponse:
        """
        Execute grounded document retrieval and question answering.
        """
        question = request.question.strip()
        target_lang = request.target_language or "en"

        # 1. Inspect question for prompt injection
        is_safe, matches = self.injection_guard.inspect_text(question)
        if not is_safe:
            return QuestionAnswerResponse(
                document_id=document_id,
                question=question,
                answer="The query could not be processed due to restricted safety patterns.",
                target_language=target_lang,
                status="RESTRICTED_QUERY",
                citations=[],
                warnings=[f"Safety pattern detected: {matches}"],
            )

        # 2. Retrieve or build isolated document index
        index = document_index_manager.get_or_create_index(tenant_id, document_id)
        if not index.chunks:
            chunks = self.chunker.chunk_document(
                document_id=document_id,
                tenant_id=tenant_id,
                text=approved_doc.clinical_content.text,
                page_number=approved_doc.extraction.pages_processed,
            )
            index.build_index(chunks)

        # 3. Vector similarity search
        ranked_results = index.search(query=question, top_k=5)

        # 4. Filter by relevance threshold
        relevant_chunks = [(chunk, score) for chunk, score in ranked_results if score >= self.relevance_threshold]

        if not relevant_chunks:
            return QuestionAnswerResponse(
                document_id=document_id,
                question=question,
                answer="The provided document does not contain sufficient evidence to answer this question.",
                target_language=target_lang,
                status="INSUFFICIENT_EVIDENCE",
                citations=[],
                warnings=["No document passages exceeded the minimum evidence relevance threshold."],
            )

        # 5. Build citations
        citations: list[Citation] = [
            self.citation_manager.create_citation_from_chunk(chunk, score) for chunk, score in relevant_chunks[:3]
        ]

        # 6. Format prompt for LLM
        prompt_template = prompt_registry.get_prompt("F_QUESTION_ANSWERING")
        evidence_str = "\n".join([f"[{c.citation_id}] {c.evidence_text}" for c in citations])

        prompt_str = prompt_template.user_template.format(
            user_question=question,
            target_language=target_lang,
            validated_clinical_facts="Refer to evidence passages.",
            retrieved_chunks=evidence_str,
        )

        response = self.llm_provider.generate_structured(
            prompt=prompt_str,
            response_model=QuestionAnswerResponse,
            system_prompt=prompt_template.system_prompt,
        )

        # Attach real verified citations
        return QuestionAnswerResponse(
            document_id=document_id,
            question=question,
            answer=response.answer,
            target_language=target_lang,
            status=response.status if response.status != "RESTRICTED_QUERY" else "ANSWERED",
            citations=citations,
            warnings=response.warnings,
        )

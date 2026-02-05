import grpc
from concurrent import futures
import logging

from proto import agent_pb2
from proto import agent_pb2_grpc
from agent import TemplateAgent
from embedding import EmbeddingService
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIServicer(agent_pb2_grpc.AIServiceServicer):
    """gRPC servicer for AI service"""
    
    def __init__(self):
        logger.info("Initializing AI Service...")
        self.agent = TemplateAgent()
        self.embedding_service = EmbeddingService()
        logger.info("AI Service initialized successfully")
    
    def UnderstandIntent(self, request, context):
        """Understand user intent and extract features"""
        try:
            logger.info(f"Understanding intent for query: {request.query}")
            
            # Call agent to analyze intent
            intent_result = self.agent.understand_intent(
                query=request.query,
                user_id=request.user_id,
                context=list(request.context)
            )
            
            logger.info(f"Intent understood: {intent_result['intent']}")
            
            return agent_pb2.IntentResponse(
                intent=intent_result['intent'],
                features=intent_result['features'],
                keywords=intent_result['keywords'],
                tags=intent_result['tags'],
                search_strategy=intent_result['search_strategy']
            )
        except Exception as e:
            logger.error(f"Intent understanding failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_pb2.IntentResponse()
    
    def GenerateEmbedding(self, request, context):
        """Generate text embedding"""
        try:
            logger.debug(f"Generating embedding for text: {request.text[:50]}...")
            
            embedding = self.embedding_service.encode(request.text)
            
            # Convert numpy array to list
            embedding_list = embedding.tolist()
            
            logger.debug(f"Embedding generated, dimension: {len(embedding_list)}")
            
            return agent_pb2.EmbeddingResponse(
                embedding=embedding_list,
                dimension=len(embedding_list)
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_pb2.EmbeddingResponse()
    
    def GenerateExplanation(self, request, context):
        """Generate recommendation explanation"""
        try:
            logger.info(f"Generating explanation for {len(request.templates)} templates")
            
            templates = [
                {
                    'template_id': t.template_id,
                    'name': t.name,
                    'description': t.description,
                    'tags': list(t.tags)
                }
                for t in request.templates
            ]
            
            explanation = self.agent.generate_explanation(
                query=request.query,
                templates=templates
            )
            
            logger.info("Explanation generated successfully")
            
            return agent_pb2.ExplanationResponse(
                explanation=explanation,
                reasons=[]  # Can add individual reasons if needed
            )
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_pb2.ExplanationResponse()


def serve():
    """Start the gRPC server"""
    # TODO: Configure server parameters
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 10 * 1024 * 1024),
            ('grpc.max_receive_message_length', 10 * 1024 * 1024),
        ]
    )
    
    agent_pb2_grpc.add_AIServiceServicer_to_server(
        AIServicer(), server
    )
    
    port = config.grpc_port
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    logger.info(f"AI Service gRPC server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)


if __name__ == '__main__':
    serve()

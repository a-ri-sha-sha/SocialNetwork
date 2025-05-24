import grpc
import time
from concurrent import futures
import post_service_pb2
import post_service_pb2_grpc
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from database import Post, Session, init_db
import os

class PostServicer(post_service_pb2_grpc.PostServiceServicer):
    def CreatePost(self, request, context):
        session = Session()
        try:
            new_post = Post(
                title=request.title,
                description=request.description,
                creator_id=request.creator_id,
                is_private=request.is_private,
                tags=list(request.tags)
            )
            session.add(new_post)
            session.commit()
            
            return post_service_pb2.Post(
                id=new_post.id,
                title=new_post.title,
                description=new_post.description,
                creator_id=new_post.creator_id,
                created_at=new_post.created_at.isoformat(),
                updated_at=new_post.updated_at.isoformat(),
                is_private=new_post.is_private,
                tags=new_post.tags
            )
        except Exception as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error creating post: {str(e)}")
            return post_service_pb2.Post()
        finally:
            session.close()
    
    def GetPost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter(Post.id == request.post_id).first()
            
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.Post()

            if post.is_private and post.creator_id != request.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("You don't have permission to view this private post")
                return post_service_pb2.Post()
            
            return post_service_pb2.Post(
                id=post.id,
                title=post.title,
                description=post.description,
                creator_id=post.creator_id,
                created_at=post.created_at.isoformat(),
                updated_at=post.updated_at.isoformat(),
                is_private=post.is_private,
                tags=post.tags
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error retrieving post: {str(e)}")
            return post_service_pb2.Post()
        finally:
            session.close()
    
    def UpdatePost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter(Post.id == request.post_id).first()
            
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.Post()

            if post.creator_id != request.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("You don't have permission to update this post")
                return post_service_pb2.Post()

            if request.title:
                post.title = request.title
            if request.description:
                post.description = request.description
            post.is_private = request.is_private
            if request.tags:
                post.tags = list(request.tags)
                
            session.commit()
            
            return post_service_pb2.Post(
                id=post.id,
                title=post.title,
                description=post.description,
                creator_id=post.creator_id,
                created_at=post.created_at.isoformat(),
                updated_at=post.updated_at.isoformat(),
                is_private=post.is_private,
                tags=post.tags
            )
        except Exception as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error updating post: {str(e)}")
            return post_service_pb2.Post()
        finally:
            session.close()
    
    def DeletePost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter(Post.id == request.post_id).first()
            
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.DeletePostResponse(success=False, message="Post not found")

            if post.creator_id != request.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("You don't have permission to delete this post")
                return post_service_pb2.DeletePostResponse(success=False, message="Permission denied")
                
            session.delete(post)
            session.commit()
            
            return post_service_pb2.DeletePostResponse(
                success=True,
                message=f"Post with ID {request.post_id} deleted successfully"
            )
        except Exception as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error deleting post: {str(e)}")
            return post_service_pb2.DeletePostResponse(success=False, message=f"Database error: {str(e)}")
        finally:
            session.close()
    
    def ListPosts(self, request, context):
        session = Session()
        try:
            page = max(1, request.page)
            per_page = min(max(1, request.per_page), 100)

            query = session.query(Post)

            query = query.filter((Post.is_private == False) | (Post.creator_id == request.user_id))

            total = query.count()

            posts = query.order_by(Post.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

            post_list = []
            for post in posts:
                post_list.append(post_service_pb2.Post(
                    id=post.id,
                    title=post.title,
                    description=post.description,
                    creator_id=post.creator_id,
                    created_at=post.created_at.isoformat(),
                    updated_at=post.updated_at.isoformat(),
                    is_private=post.is_private,
                    tags=post.tags
                ))
                
            return post_service_pb2.ListPostsResponse(
                posts=post_list,
                total=total,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error listing posts: {str(e)}")
            return post_service_pb2.ListPostsResponse()
        finally:
            session.close()

def serve():
    init_db()

    port = os.environ.get('GRPC_PORT', '50052')

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    post_service_pb2_grpc.add_PostServiceServicer_to_server(PostServicer(), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Post Service gRPC server started on port {port}")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
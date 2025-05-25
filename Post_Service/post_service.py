import grpc
import time
from concurrent import futures
import post_service_pb2
import post_service_pb2_grpc
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ARRAY
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from database import Post, Session, init_db, Comment, PostView, PostLike
from kafka_producer import send_post_view_event, send_post_like_event, send_post_comment_event
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

    def ViewPost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter(Post.id == request.post_id).first()
            
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.ViewPostResponse(success=False, views_count=0)

            existing_view = session.query(PostView).filter(
                PostView.post_id == request.post_id,
                PostView.user_id == request.user_id
            ).first()
            
            if not existing_view:
                new_view = PostView(post_id=request.post_id, user_id=request.user_id)
                session.add(new_view)

                post.views_count += 1
                
                session.commit()

                send_post_view_event(request.user_id, request.post_id, new_view.viewed_at)
            
            return post_service_pb2.ViewPostResponse(
                success=True,
                views_count=post.views_count
            )
        except Exception as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error viewing post: {str(e)}")
            return post_service_pb2.ViewPostResponse(success=False, views_count=0)
        finally:
            session.close()
    
    def LikePost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter(Post.id == request.post_id).first()
            
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.LikePostResponse(success=False, likes_count=0)

            existing_like = session.query(PostLike).filter(
                PostLike.post_id == request.post_id,
                PostLike.user_id == request.user_id
            ).first()
            
            if existing_like:
                if existing_like.is_like != request.is_like:
                    existing_like.is_like = request.is_like

                    if request.is_like:
                        post.likes_count += 2
                    else:
                        post.likes_count -= 2
                    
                    send_post_like_event(request.user_id, request.post_id, request.is_like)
            else:
                new_like = PostLike(
                    post_id=request.post_id,
                    user_id=request.user_id,
                    is_like=request.is_like
                )
                session.add(new_like)

                if request.is_like:
                    post.likes_count += 1
                else:
                    post.likes_count -= 1
                
                send_post_like_event(request.user_id, request.post_id, request.is_like)
            
            session.commit()
            
            return post_service_pb2.LikePostResponse(
                success=True,
                likes_count=post.likes_count
            )
        except Exception as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error liking post: {str(e)}")
            return post_service_pb2.LikePostResponse(success=False, likes_count=0)
        finally:
            session.close()

    def CommentPost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter(Post.id == request.post_id).first()
            
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.Comment()

            new_comment = Comment(
                post_id=request.post_id,
                user_id=request.user_id,
                text=request.text
            )
            session.add(new_comment)
            session.commit()

            send_post_comment_event(
                request.user_id,
                request.post_id,
                new_comment.id,
                new_comment.created_at
            )
            
            return post_service_pb2.Comment(
                id=new_comment.id,
                post_id=new_comment.post_id,
                user_id=new_comment.user_id,
                text=new_comment.text,
                created_at=new_comment.created_at.isoformat()
            )
        except Exception as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error commenting on post: {str(e)}")
            return post_service_pb2.Comment()
        finally:
            session.close()
    
    def GetPostComments(self, request, context):
        session = Session()
        try:
            post = session.query(Post).filter(Post.id == request.post_id).first()
            
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.GetPostCommentsResponse()

            page = max(1, request.page)
            per_page = min(max(1, request.per_page), 100)

            total = session.query(func.count(Comment.id)).filter(Comment.post_id == request.post_id).scalar()
            
            comments = session.query(Comment).filter(
                Comment.post_id == request.post_id
            ).order_by(
                Comment.created_at.desc()
            ).offset(
                (page - 1) * per_page
            ).limit(per_page).all()

            comment_list = []
            for comment in comments:
                comment_list.append(post_service_pb2.Comment(
                    id=comment.id,
                    post_id=comment.post_id,
                    user_id=comment.user_id,
                    text=comment.text,
                    created_at=comment.created_at.isoformat()
                ))
            
            return post_service_pb2.GetPostCommentsResponse(
                comments=comment_list,
                total=total,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting post comments: {str(e)}")
            return post_service_pb2.GetPostCommentsResponse()
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
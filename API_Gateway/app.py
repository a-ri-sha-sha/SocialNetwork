from flask import Flask, request, jsonify
import os
import requests
import grpc
import jwt
import post_service_pb2
import post_service_pb2_grpc
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')

SERVICES = {
    "user": os.environ.get("USER_SERVICE_URL", "http://user_service:5001"),
    "post": os.environ.get("POST_SERVICE_URL", "post_service:50051")
}

def get_post_service_stub():
    channel = grpc.insecure_channel(SERVICES["post"])
    return post_service_pb2_grpc.PostServiceStub(channel)

def authenticate_user(request):
    token = request.headers.get('Authorization')
    if not token:
        return None, {'error': 'Authentication token is missing'}, 401
    
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        
        user_response = requests.get(
            f"{SERVICES['user']}/profile",
            headers={"Authorization": token}
        )
        
        if user_response.status_code != 200:
            return None, {'error': 'Failed to validate user'}, 401
        
        user_data = user_response.json()
        return user_data, None, None
    
    except jwt.ExpiredSignatureError:
        return None, {'error': 'Token has expired'}, 401
    except jwt.InvalidTokenError:
        return None, {'error': 'Invalid token'}, 401

@app.route('/user/<path:path>', methods=['POST', 'GET', 'PUT', 'DELETE', 'PATCH'])
def proxy_user_service(path):
    url = f'{SERVICES["user"]}/{path}'
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}

    json_data = None
    if request.method in ['POST', 'PUT', 'PATCH'] and request.is_json:
        json_data = request.get_json()
    
    response = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        json=json_data,
        params=request.args
    )

    resp_headers = {
        key: value for key, value in response.headers.items()
        if key.lower() in ['content-type', 'content-length', 'content-encoding']
    }
    
    return response.content, response.status_code, resp_headers

@app.route('/posts', methods=['POST'])
def create_post():
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    data = request.get_json()
    
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    if not data.get('description'):
        return jsonify({'error': 'Description is required'}), 400
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.CreatePostRequest(
            title=data.get('title'),
            description=data.get('description'),
            creator_id=user_data['id'],
            is_private=data.get('is_private', False),
            tags=data.get('tags', [])
        )
        
        response = stub.CreatePost(grpc_request)
        
        post_data = {
            'id': response.id,
            'title': response.title,
            'description': response.description,
            'creator_id': response.creator_id,
            'created_at': response.created_at,
            'updated_at': response.updated_at,
            'is_private': response.is_private,
            'tags': list(response.tags)
        }
        
        return jsonify(post_data), 201
    
    except grpc.RpcError as e:
        status_code = e.code()
        
        if status_code == grpc.StatusCode.INTERNAL:
            return jsonify({'error': 'Internal server error'}), 500
        elif status_code == grpc.StatusCode.INVALID_ARGUMENT:
            return jsonify({'error': str(e.details())}), 400
        else:
            return jsonify({'error': str(e.details())}), 500


@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.GetPostRequest(
            post_id=post_id,
            user_id=user_data['id']
        )
        
        response = stub.GetPost(grpc_request)
        
        post_data = {
            'id': response.id,
            'title': response.title,
            'description': response.description,
            'creator_id': response.creator_id,
            'created_at': response.created_at,
            'updated_at': response.updated_at,
            'is_private': response.is_private,
            'tags': list(response.tags)
        }
        
        return jsonify(post_data), 200
    
    except grpc.RpcError as e:
        try:
            status_code = e.code()
        except AttributeError:
            status_code = e._code
        
        if status_code == grpc.StatusCode.NOT_FOUND:
            return jsonify({'error': 'Post not found'}), 404
        elif status_code == grpc.StatusCode.PERMISSION_DENIED:
            return jsonify({'error': 'You do not have permission to view this post'}), 403
        else:
            return jsonify({'error': str(e)}), 500

@app.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    data = request.get_json()
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.UpdatePostRequest(
            post_id=post_id,
            title=data.get('title', ''),
            description=data.get('description', ''),
            user_id=user_data['id'],
            is_private=data.get('is_private', False),
            tags=data.get('tags', [])
        )
        
        response = stub.UpdatePost(grpc_request)
        
        post_data = {
            'id': response.id,
            'title': response.title,
            'description': response.description,
            'creator_id': response.creator_id,
            'created_at': response.created_at,
            'updated_at': response.updated_at,
            'is_private': response.is_private,
            'tags': list(response.tags)
        }
        
        return jsonify(post_data), 200
    
    except grpc.RpcError as e:
        status_code = e.code()
        
        if status_code == grpc.StatusCode.NOT_FOUND:
            return jsonify({'error': 'Post not found'}), 404
        elif status_code == grpc.StatusCode.PERMISSION_DENIED:
            return jsonify({'error': 'You do not have permission to update this post'}), 403
        else:
            return jsonify({'error': str(e.details())}), 500


@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.DeletePostRequest(
            post_id=post_id,
            user_id=user_data['id']
        )

        response = stub.DeletePost(grpc_request)

        return jsonify({
            'success': response.success,
            'message': response.message
        }), 200 if response.success else 400
    
    except grpc.RpcError as e:
        status_code = e.code()
        
        if status_code == grpc.StatusCode.NOT_FOUND:
            return jsonify({'error': 'Post not found'}), 404
        elif status_code == grpc.StatusCode.PERMISSION_DENIED:
            return jsonify({'error': 'You do not have permission to delete this post'}), 403
        else:
            return jsonify({'error': str(e.details())}), 500


@app.route('/posts', methods=['GET'])
def list_posts():
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.ListPostsRequest(
            page=page,
            per_page=per_page,
            user_id=user_data['id']
        )

        response = stub.ListPosts(grpc_request)

        posts = []
        for post in response.posts:
            posts.append({
                'id': post.id,
                'title': post.title,
                'description': post.description,
                'creator_id': post.creator_id,
                'created_at': post.created_at,
                'updated_at': post.updated_at,
                'is_private': post.is_private,
                'tags': list(post.tags)
            })
        
        return jsonify({
            'posts': posts,
            'total': response.total,
            'page': response.page,
            'per_page': response.per_page
        }), 200
    
    except grpc.RpcError as e:
        return jsonify({'error': str(e.details())}), 500

@app.route('/posts/<int:post_id>/view', methods=['POST'])
def view_post(post_id):
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.ViewPostRequest(
            post_id=post_id,
            user_id=user_data['id']
        )
        
        response = stub.ViewPost(grpc_request)
        
        return jsonify({
            'success': response.success,
            'views_count': response.views_count
        }), 200
    
    except grpc.RpcError as e:
        status_code = e.code()
        
        if status_code == grpc.StatusCode.NOT_FOUND:
            return jsonify({'error': 'Post not found'}), 404
        else:
            return jsonify({'error': str(e)}), 500

@app.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    data = request.get_json()
    is_like = data.get('is_like', True)
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.LikePostRequest(
            post_id=post_id,
            user_id=user_data['id'],
            is_like=is_like
        )
        
        response = stub.LikePost(grpc_request)
        
        return jsonify({
            'success': response.success,
            'likes_count': response.likes_count
        }), 200
    
    except grpc.RpcError as e:
        status_code = e.code()
        
        if status_code == grpc.StatusCode.NOT_FOUND:
            return jsonify({'error': 'Post not found'}), 404
        else:
            return jsonify({'error': str(e)}), 500

@app.route('/posts/<int:post_id>/comments', methods=['POST'])
def comment_post(post_id):
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    data = request.get_json()
    if not data.get('text'):
        return jsonify({'error': 'Comment text is required'}), 400
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.CommentPostRequest(
            post_id=post_id,
            user_id=user_data['id'],
            text=data.get('text')
        )
        
        response = stub.CommentPost(grpc_request)
        
        return jsonify({
            'id': response.id,
            'post_id': response.post_id,
            'user_id': response.user_id,
            'text': response.text,
            'created_at': response.created_at
        }), 201
    
    except grpc.RpcError as e:
        status_code = e.code()
        
        if status_code == grpc.StatusCode.NOT_FOUND:
            return jsonify({'error': 'Post not found'}), 404
        else:
            return jsonify({'error': str(e)}), 500

@app.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    user_data, error, status_code = authenticate_user(request)
    if error:
        return jsonify(error), status_code
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    try:
        stub = get_post_service_stub()
        grpc_request = post_service_pb2.GetPostCommentsRequest(
            post_id=post_id,
            page=page,
            per_page=per_page
        )
        
        response = stub.GetPostComments(grpc_request)
        
        comments = []
        for comment in response.comments:
            comments.append({
                'id': comment.id,
                'post_id': comment.post_id,
                'user_id': comment.user_id,
                'text': comment.text,
                'created_at': comment.created_at
            })
        
        return jsonify({
            'comments': comments,
            'total': response.total,
            'page': response.page,
            'per_page': response.per_page
        }), 200
    
    except grpc.RpcError as e:
        status_code = e.code()
        
        if status_code == grpc.StatusCode.NOT_FOUND:
            return jsonify({'error': 'Post not found'}), 404
        else:
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

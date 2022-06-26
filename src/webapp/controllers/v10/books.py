from fastapi import APIRouter

router = APIRouter(tags=['books'], prefix='/books')


@router.get('/')
def get_books():

    return {'books': [{'id': 1, 'title': 'Book 1'}, {'id': 2, 'title': 'Book 2'}]}

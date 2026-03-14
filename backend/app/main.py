from fastapi import FastAPI

app = FastAPI() # This sets up the FastAPI application instance


@app.get("/")
def read_root():
    '''
    Root endpoint

    :return: A simple JSON response with a greeting message
    '''
    return {"Hello": "World"}
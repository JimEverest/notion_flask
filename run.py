from app import app

if __name__ == '__main__':
    # app.run( port=5001)
    app.run(host='0.0.0.0', port=8083,debug=True)

mod admin_middleware;

use poem::{Route, Server, handler, listener::TcpListener};

#[handler]
fn publish_post() {
    todo!();
}

#[tokio::main]
async fn main() -> Result<(), std::io::Error> {
    let app = Route::new().at("/publish", publish_post);

    Server::new(TcpListener::bind("0.0.0.0:3000"))
        .run(app)
        .await
}

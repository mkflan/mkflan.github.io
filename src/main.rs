#![allow(unused)]

mod admin_middleware;

use poem::{
    EndpointExt, Route, Server,
    endpoint::{StaticFileEndpoint, StaticFilesEndpoint},
    get, handler,
    listener::TcpListener,
    web::Multipart,
};
use std::path::Path;

const MANIFEST: &'static str = env!("CARGO_MANIFEST_DIR");

#[handler]
async fn publish_post(mut multipart: Multipart) {
    while let Ok(Some(field)) = multipart.next_field().await {
        let file_name = field
            .file_name()
            .map(ToString::to_string)
            .expect("unable to extract file name");

        todo!();
    }
}

#[tokio::main]
async fn main() -> Result<(), std::io::Error> {
    // TODO: can I extract the static endpoints into separate #[handler]'s to clean up the code?
    let app = Route::new()
        .nest(
            "/",
            StaticFilesEndpoint::new(Path::new(MANIFEST).join("public"))
                .show_files_listing()
                .index_file("index.html"),
        )
        .at(
            "/publish",
            get(StaticFileEndpoint::new(
                Path::new(MANIFEST).join("public/publish.html"),
            ))
            .post(publish_post), /* TODO: add admin middleware */
        );

    Server::new(TcpListener::bind("0.0.0.0:3000"))
        .run(app)
        .await
}

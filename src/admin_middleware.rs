use poem::{Endpoint, Middleware};

/// Middleware for authentication to restricted endpoints.
pub struct AdminMiddleware;

// impl<E: Endpoint> Middleware<E> for AdminMiddleware {
// type Output = ;

//     fn transform(&self, ep: E) -> Self::Output {
//         todo!();
//     }
// }

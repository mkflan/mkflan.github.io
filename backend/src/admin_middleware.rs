use poem::{Endpoint, Middleware};

/// Middleware for admin authentication to special endpoints.
pub struct AdminMiddleware;

// impl<E: Endpoint> Middleware<E> for AdminMiddleware {
// type Output = ;

//     fn transform(&self, ep: E) -> Self::Output {
//         todo!();
//     }
// }

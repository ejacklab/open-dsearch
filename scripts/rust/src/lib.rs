pub mod fetch;
pub mod rank;
pub mod search;

pub use fetch::{fetch_url, FetchedPage};
pub use rank::{score_and_rank, ScoredResult, SourceType};
pub use search::{
    expand_queries, expand_queries_with_sources, search_gemini, search_minimax, 
    search_xai, search_xai_with_params, xai_x_search, xai_x_search_with_params,
    search_with_fallback, synthesize_with_llm, SearchResult, XaiSearchParams
};

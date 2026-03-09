import jwt from 'jsonwebtoken';

/**
 * JWT Validation Middleware for Express.js
 * 
 * Validates JWT from Authorization header (Bearer token format).
 * Extracts user_id from token's 'sub' claim and attaches to req.user_id.
 * 
 * Usage:
 *   app.use(verifyAuthToken);  // Apply globally to all routes
 *   OR
 *   app.post('/protected', verifyAuthToken, handler);  // Apply to specific route
 */

export const verifyAuthToken = (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader) {
            return res.status(401).json({
                error: 'Authorization header missing',
                detail: 'Please provide an Authorization: Bearer <token> header'
            });
        }

        if (!authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
                error: 'Invalid authorization header format',
                detail: 'Authorization header must start with "Bearer "'
            });
        }

        const token = authHeader.slice(7); // Remove "Bearer " prefix

        try {
            const payload = jwt.verify(token, process.env.JWT_SECRET_KEY, {
                algorithms: [process.env.JWT_ALGORITHM || 'HS256']
            });

            // Extract user_id from 'sub' claim (standard JWT claim for subject/user)
            const userId = payload.sub;

            if (!userId) {
                return res.status(401).json({
                    error: 'Invalid token',
                    detail: 'Token is missing "sub" (user) claim'
                });
            }

            // Attach user_id to request object for downstream middleware/handlers
            req.user_id = userId;
            next();

        } catch (jwtError) {
            if (jwtError.name === 'TokenExpiredError') {
                return res.status(401).json({
                    error: 'Token expired',
                    detail: 'Your authentication token has expired. Please log in again.'
                });
            }
            if (jwtError.name === 'JsonWebTokenError') {
                return res.status(401).json({
                    error: 'Invalid token',
                    detail: 'The provided token is invalid or malformed'
                });
            }
            return res.status(401).json({
                error: 'Authentication failed',
                detail: jwtError.message
            });
        }

    } catch (err) {
        console.error('Auth middleware error:', err);
        return res.status(500).json({
            error: 'Internal server error',
            detail: 'An error occurred during authentication'
        });
    }
};

/**
 * Validates X-Service-Token header for internal service-to-service communication.
 * 
 * Used by Filter Engine and Enrichment Service to verify requests come from MCP Server.
 */
export const verifyServiceToken = (req, res, next) => {
    const serviceToken = req.headers['x-service-token'];

    if (!serviceToken) {
        return res.status(403).json({
            error: 'Service token missing',
            detail: 'X-Service-Token header required'
        });
    }

    if (serviceToken !== process.env.INTERNAL_SERVICE_TOKEN) {
        return res.status(403).json({
            error: 'Invalid service token',
            detail: 'Unauthorized service'
        });
    }

    next();
};
